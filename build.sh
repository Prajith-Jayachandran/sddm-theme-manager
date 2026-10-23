#!/usr/bin/env bash
# SDDM Theme Manager - Standalone Binary Build Script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=============================================="
echo " Building SDDM Theme Manager Standalone Binary"
echo "=============================================="

# Check for pyinstaller
if command -v pyinstaller &>/dev/null; then
    PYINSTALLER_CMD="pyinstaller"
elif command -v uvx &>/dev/null; then
    PYINSTALLER_CMD="uvx pyinstaller"
else
    echo "Error: Neither 'pyinstaller' nor 'uvx' was found."
    echo "Install PyInstaller via package manager or 'uv tool install pyinstaller'."
    exit 1
fi

echo "Using: $PYINSTALLER_CMD"

$PYINSTALLER_CMD \
    --name sddm-theme-manager \
    --onefile \
    --windowed \
    --clean \
    --noconfirm \
    --add-data "ui/styles.qss:ui" \
    --add-data "resources:resources" \
    --icon "resources/icons/sddm-theme-manager.png" \
    main.py

echo ""
echo "Build complete! Standalone binary located at:"
echo "  $SCRIPT_DIR/dist/sddm-theme-manager"
