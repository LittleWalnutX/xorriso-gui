#!/usr/bin/env bash
set -euo pipefail

APP_NAME="xorriso-gui"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build_appimage"
APPDIR="$BUILD_DIR/${APP_NAME}.AppDir"

echo "=== Building $APP_NAME AppImage ==="

echo "Step 1: PyInstaller bundle (onedir)..."
rm -rf "$BUILD_DIR"
cd "$SCRIPT_DIR"

python3.14 -m PyInstaller \
    --onedir \
    --windowed \
    --name "$APP_NAME" \
    --add-data "xorriso_gui/assets:xorriso_gui/assets" \
    --collect-all "PySide6" \
    --distpath "$BUILD_DIR/dist" \
    --workpath "$BUILD_DIR/build" \
    -y \
    main.py 2>&1 | tail -5

echo "Step 2: Bundle xorriso and dependencies..."
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

echo "Step 3: Package AppImage..."
if command -v appimagetool &>/dev/null; then
    ARCH=x86_64 appimagetool "$APPDIR" "$BUILD_DIR/${APP_NAME}-$(date +%Y%m%d)-x86_64.AppImage"
    echo "=== AppImage created at: $BUILD_DIR/${APP_NAME}-*.AppImage ==="
elif [ -x /tmp/appimagetool ]; then
    ARCH=x86_64 /tmp/appimagetool "$APPDIR" "$BUILD_DIR/${APP_NAME}-$(date +%Y%m%d)-x86_64.AppImage"
    echo "=== AppImage created at: $BUILD_DIR/${APP_NAME}-*.AppImage ==="
else
    echo ""
    echo "=== AppDir prepared at: $APPDIR ==="
    echo "To create AppImage, install appimagetool:"
    echo "  wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    echo "  chmod +x appimagetool-x86_64.AppImage"
    echo "  ./appimagetool-x86_64.AppImage $APPDIR $BUILD_DIR/xorriso-gui-x86_64.AppImage"
    echo ""
    echo "Or test the app directly:"
    echo "  $APPDIR/AppRun"
fi