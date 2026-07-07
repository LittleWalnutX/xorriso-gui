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

pyinstaller \
    --onedir \
    --windowed \
    --name "$APP_NAME" \
    --add-data "xorriso_gui/assets:xorriso_gui/assets" \
    --hidden-import="PySide6.QtCore" \
    --hidden-import="PySide6.QtWidgets" \
    --hidden-import="PySide6.QtGui" \
    --distpath "$BUILD_DIR/dist" \
    --workpath "$BUILD_DIR/build" \
    -y \
    main.py 2>&1 | tail -5

echo "Step 2: Create AppDir..."
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"

cp -r "$BUILD_DIR/dist/${APP_NAME}/"* "$APPDIR/usr/bin/"
ln -sf usr/bin/xorriso-gui "$APPDIR/AppRun"

cp "$SCRIPT_DIR/xorriso-gui.desktop" "$APPDIR/"
cp "$SCRIPT_DIR/xorriso_gui/assets/icon.svg" "$APPDIR/xorriso-gui.svg"

echo "Step 3: Check for appimagetool..."
if command -v appimagetool &>/dev/null; then
    ARCH=x86_64 appimagetool "$APPDIR" "$BUILD_DIR/${APP_NAME}-$(date +%Y%m%d)-x86_64.AppImage"
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