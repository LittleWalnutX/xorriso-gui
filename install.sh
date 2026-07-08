#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"

echo "=== Installing xorriso-gui ==="
echo "Project directory: $SCRIPT_DIR"

if ! command -v python3 &>/dev/null; then
    echo "错误: 未找到 python3"
    exit 1
fi

echo "Step 1: Install Python dependencies..."
python3 -m pip install -r "$SCRIPT_DIR/requirements.txt" 2>&1 | tail -3

echo "Step 2: Install desktop entry..."
mkdir -p ~/.local/share/applications ~/.local/share/icons

sed "s|__PROJECT_DIR__|$SCRIPT_DIR|g" \
    "$SCRIPT_DIR/xorriso-gui.desktop.in" \
    > ~/.local/share/applications/xorriso-gui.desktop

cp "$SCRIPT_DIR/xorriso_gui/assets/icon.svg" ~/.local/share/icons/xorriso-gui.svg

echo "Done! xorriso-gui is now available in your application menu."