#!/usr/bin/env bash
set -euo pipefail

APP_NAME="xorriso-gui"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build_appimage"
APPDIR="$BUILD_DIR/${APP_NAME}.AppDir"

echo "=== Building $APP_NAME AppImage (optimized) ==="

echo "Step 1: PyInstaller bundle (onedir, optimized)..."
rm -rf "$BUILD_DIR"
cd "$SCRIPT_DIR"

python3.14 -m PyInstaller \
    --onedir \
    --windowed \
    --name "$APP_NAME" \
    --add-data "xorriso_gui/assets:xorriso_gui/assets" \
    --collect-all "PySide6" \
    --exclude-module tkinter \
    --exclude-module sqlite3 \
    --exclude-module xmlrpc \
    --exclude-module multiprocessing \
    --exclude-module concurrent.futures \
    --exclude-module asyncio \
    --exclude-module email \
    --exclude-module http \
    --exclude-module urllib \
    --exclude-module unittest \
    --exclude-module test \
    --exclude-module pydoc \
    --exclude-module logging \
    --exclude-module argparse \
    --distpath "$BUILD_DIR/dist" \
    --workpath "$BUILD_DIR/build" \
    -y \
    main.py 2>&1 | tail -5

echo "Step 2: Strip unused Qt modules..."
INTERNAL="$BUILD_DIR/dist/${APP_NAME}/_internal"

strip_unused() {
    local base="$INTERNAL/PySide6/Qt"
    local bin="$INTERNAL"

    echo "  Removing QtWebEngine (~250MB)..."
    rm -rf "$base"/lib/libQt6WebEngine* 2>/dev/null || true
    rm -rf "$base"/lib/libQt6Pdf* 2>/dev/null || true
    rm -rf "$base"/resources/qtwebengine* 2>/dev/null || true
    rm -rf "$base"/translations/qtwebengine_locales 2>/dev/null || true
    find "$INTERNAL" -name '*QtWebEngine*' -delete 2>/dev/null || true
    find "$INTERNAL" -name '*QtWebChannel*' -delete 2>/dev/null || true
    find "$INTERNAL" -name '*QtPdf*' -delete 2>/dev/null || true

    echo "  Removing QtQuick/QML (~50MB)..."
    rm -rf "$base"/qml 2>/dev/null || true
    rm -rf "$base"/lib/libQt6Quick* 2>/dev/null || true
    rm -rf "$base"/lib/libQt6Qml* 2>/dev/null || true
    find "$INTERNAL" -name '*QtQuick*' -delete 2>/dev/null || true
    find "$INTERNAL" -name '*QtQml*' -delete 2>/dev/null || true

    echo "  Removing FFmpeg libs (~15MB)..."
    rm -f "$INTERNAL"/libavcodec* "$INTERNAL"/libavformat* "$INTERNAL"/libavutil* 2>/dev/null || true
    rm -f "$INTERNAL"/libswresample* "$INTERNAL"/libswscale* 2>/dev/null || true
    rm -f "$base"/lib/libavcodec* "$base"/lib/libavformat* "$base"/lib/libavutil* 2>/dev/null || true
    rm -f "$base"/lib/libswresample* "$base"/lib/libswscale* 2>/dev/null || true

    echo "  Removing unused Qt .so libs..."
    KEEP_LIBS="Qt6Core Qt6Gui Qt6Widgets Qt6XcbQpa Qt6WaylandClient Qt6WlShellIntegration Qt6Concurrent icu icudata Qt6DBus"
    LIBDIR="$base/lib"
    for lib in "$LIBDIR"/lib*.so*; do
        if [ ! -f "$lib" ]; then continue; fi
        name=$(basename "$lib")
        keep=0
        for k in $KEEP_LIBS; do
            if echo "$name" | grep -q "$k"; then keep=1; break; fi
        done
        if [ $keep -eq 0 ] && echo "$name" | grep -q "Qt6\|libicu"; then
            rm -f "$lib"
        fi
    done

    echo "  Removing unused PySide6 Python bindings..."
    for f in "$INTERNAL"/PySide6/*.abi3.so; do
        name=$(basename "$f")
        if [ ! -f "$f" ]; then continue; fi
        case "$name" in
            QtCore.*|QtGui.*|QtWidgets.*|QtWaylandClient.*|QtDBus.*|QtConcurrent.*|__init__.*) ;;
            *) rm -f "$f" ;;
        esac
    done

    echo "  Removing unused Qt plugins..."
    PLUGDIR="$base/plugins"
    for dir in gamepads geometryloaders renderplugins sceneparsers sensorgestures sensors sqldrivers texttospeech virtualkeyboard webview; do
        rm -rf "$PLUGDIR/$dir" 2>/dev/null || true
    done

    echo "  Removing unused metatypes..."
    shopt -s nullglob
    for f in "$base"/metatypes/qt6*_*.json; do
        if [ ! -f "$f" ]; then continue; fi
        name=$(basename "$f")
        case "$name" in
            qt6core_*|qt6gui_*|qt6widgets_*|qt6waylandclient_*|qt6dbus_*|qt6concurrent_*) ;;
            *) rm -f "$f" ;;
        esac
    done
}

strip_unused

BEFORE=$(du -sh "$INTERNAL" 2>/dev/null | cut -f1)
echo "  Internal dir size after strip: $BEFORE"

echo "Step 3: Bundle xorriso and dependencies..."
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/lib"

cp -r "$BUILD_DIR/dist/${APP_NAME}/"* "$APPDIR/usr/bin/"

XORRISO_BIN="$(which xorriso)"
cp "$XORRISO_BIN" "$APPDIR/usr/bin/"

for lib in $(ldd "$XORRISO_BIN" 2>/dev/null | awk '/=> \//{print $3}'); do
    cp "$lib" "$APPDIR/usr/lib/"
done

cat > "$APPDIR/AppRun" << 'APPRUN'
#!/usr/bin/env bash
HERE="$(cd "$(dirname "$0")" && pwd)"
export LD_LIBRARY_PATH="$HERE/usr/lib:$LD_LIBRARY_PATH"
export PATH="$HERE/usr/bin:$PATH"
exec "$HERE/usr/bin/xorriso-gui" "$@"
APPRUN
chmod +x "$APPDIR/AppRun"

cp "$SCRIPT_DIR/xorriso-gui.desktop" "$APPDIR/"
cp "$SCRIPT_DIR/xorriso_gui/assets/icon.svg" "$APPDIR/xorriso-gui.svg"

echo "Step 4: Package AppImage..."
if command -v appimagetool &>/dev/null; then
    ARCH=x86_64 appimagetool "$APPDIR" "$BUILD_DIR/${APP_NAME}-$(date +%Y%m%d)-x86_64.AppImage"
    SIZE=$(ls -lh "$BUILD_DIR"/${APP_NAME}-*.AppImage 2>/dev/null | awk '{print $5}')
    echo "=== AppImage created: $SIZE ==="
elif [ -x /tmp/appimagetool ]; then
    ARCH=x86_64 /tmp/appimagetool "$APPDIR" "$BUILD_DIR/${APP_NAME}-$(date +%Y%m%d)-x86_64.AppImage"
    SIZE=$(ls -lh "$BUILD_DIR"/${APP_NAME}-*.AppImage 2>/dev/null | awk '{print $5}')
    echo "=== AppImage created: $SIZE ==="
else
    echo ""
    echo "=== AppDir prepared at: $APPDIR ==="
    echo "To create AppImage, install appimagetool."
    echo "Or test the app: $APPDIR/AppRun"
fi