#!/usr/bin/env bash
# ==============================================================================
# SDDM Theme Manager - Installation Script
# Supports system-wide install (/usr/local), user install (~/.local),
# or custom directory, desktop entry, icons, and Polkit rules installation.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="sddm-theme-manager"

MODE=""
PREFIX=""
POLKIT_INSTALL=true
UNINSTALL=false

show_help() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Options:
  --system           Install system-wide to /usr/local (requires sudo/root) [Default]
  --user             Install to user home directory (~/.local) without root
  --prefix <PATH>    Specify custom installation prefix (e.g., /opt, /usr)
  --no-polkit        Skip copying the Polkit rules file to /etc/polkit-1/rules.d/
  --uninstall        Uninstall and remove all installed files
  -h, --help         Show this help message

Examples:
  sudo ./install.sh                     # Full system installation with Polkit rules
  ./install.sh --user                   # User-level installation without root
  sudo ./install.sh --uninstall         # Remove system installation
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --system)
            MODE="system"
            shift
            ;;
        --user)
            MODE="user"
            PREFIX="$HOME/.local"
            POLKIT_INSTALL=false
            shift
            ;;
        --prefix)
            PREFIX="$2"
            shift 2
            ;;
        --no-polkit)
            POLKIT_INSTALL=false
            shift
            ;;
        --uninstall)
            UNINSTALL=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Auto-detect default prefix based on privilege level
if [ -z "$PREFIX" ]; then
    if [ "$EUID" -eq 0 ]; then
        MODE="system"
        PREFIX="/usr/local"
        POLKIT_INSTALL=true
    else
        MODE="user"
        PREFIX="$HOME/.local"
        POLKIT_INSTALL=false
    fi
fi

# Define target paths
BIN_DIR="$PREFIX/bin"
SHARE_DIR="$PREFIX/share"
APP_DIR="$SHARE_DIR/$APP_NAME"
DESKTOP_DIR="$SHARE_DIR/applications"
ICON_SCALABLE_DIR="$SHARE_DIR/icons/hicolor/scalable/apps"
ICON_PNG_DIR="$SHARE_DIR/icons/hicolor/256x256/apps"
POLKIT_RULE_DIR="/etc/polkit-1/rules.d"
POLKIT_RULE_FILE="$POLKIT_RULE_DIR/40-sddm-theme-manager.rules"

# -----------------------------------------------------------------------------
# UNINSTALLATION ROUTINE
# -----------------------------------------------------------------------------
if [ "$UNINSTALL" = true ]; then
    if [ -f "$SCRIPT_DIR/uninstall.sh" ]; then
        exec "$SCRIPT_DIR/uninstall.sh" "$@"
    fi

    echo "=============================================="
    echo " Uninstalling SDDM Theme Manager"
    echo "=============================================="

    echo "Removing executable wrapper: $BIN_DIR/$APP_NAME"
    rm -f "$BIN_DIR/$APP_NAME"

    echo "Removing application directory: $APP_DIR"
    rm -rf "$APP_DIR"

    echo "Removing desktop shortcut: $DESKTOP_DIR/$APP_NAME.desktop"
    rm -f "$DESKTOP_DIR/$APP_NAME.desktop"

    echo "Removing icons..."
    rm -f "$ICON_SCALABLE_DIR/$APP_NAME.svg"
    rm -f "$ICON_PNG_DIR/$APP_NAME.png"

    if [ -f "$POLKIT_RULE_FILE" ]; then
        if [ "$EUID" -eq 0 ]; then
            echo "Removing Polkit rule: $POLKIT_RULE_FILE"
            rm -f "$POLKIT_RULE_FILE"
        else
            echo "Note: Polkit rule ($POLKIT_RULE_FILE) requires root to remove:"
            echo "  sudo rm -f $POLKIT_RULE_FILE"
        fi
    fi

    if command -v update-desktop-database &>/dev/null; then
        update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    fi

    echo "Uninstallation complete!"
    exit 0
fi

# -----------------------------------------------------------------------------
# INSTALLATION ROUTINE
# -----------------------------------------------------------------------------
echo "=============================================="
echo " Installing SDDM Theme Manager"
echo " Prefix: $PREFIX"
echo " Mode:   $MODE"
echo "=============================================="

if [ "$MODE" = "system" ] && [ "$EUID" -ne 0 ]; then
    echo "Notice: System-wide installation typically requires root privileges."
    echo "If permission is denied, run with: sudo ./install.sh"
    echo ""
fi

# Create target directories
mkdir -p "$BIN_DIR"
mkdir -p "$APP_DIR"
mkdir -p "$DESKTOP_DIR"
mkdir -p "$ICON_SCALABLE_DIR"
mkdir -p "$ICON_PNG_DIR"

# Copy source code and assets
echo "Copying application files to $APP_DIR..."
cp -r "$SCRIPT_DIR/main.py" "$APP_DIR/"
cp -r "$SCRIPT_DIR/core" "$APP_DIR/"
cp -r "$SCRIPT_DIR/ui" "$APP_DIR/"
cp -r "$SCRIPT_DIR/resources" "$APP_DIR/"
[ -f "$SCRIPT_DIR/README.md" ] && cp "$SCRIPT_DIR/README.md" "$APP_DIR/"
[ -d "$SCRIPT_DIR/sddm_theme_manager" ] && cp -r "$SCRIPT_DIR/sddm_theme_manager" "$APP_DIR/"
chmod -R a+rX "$APP_DIR"

# Create launcher executable script in bin directory
echo "Creating launcher in $BIN_DIR/$APP_NAME..."
cat << EOF > "$BIN_DIR/$APP_NAME"
#!/usr/bin/env bash
exec /usr/bin/python3 "$APP_DIR/main.py" "\$@"
EOF
chmod 755 "$BIN_DIR/$APP_NAME"

# Install Desktop Entry with absolute executable path
echo "Installing desktop entry to $DESKTOP_DIR..."
sed "s|^Exec=.*|Exec=$BIN_DIR/$APP_NAME|" "$SCRIPT_DIR/resources/sddm-theme-manager.desktop" > "$DESKTOP_DIR/$APP_NAME.desktop"
chmod 644 "$DESKTOP_DIR/$APP_NAME.desktop"

# Install Icons
echo "Installing application icons..."
cp "$SCRIPT_DIR/resources/icons/sddm-theme-manager.svg" "$ICON_SCALABLE_DIR/"
chmod 644 "$ICON_SCALABLE_DIR/$APP_NAME.svg"

if [ -f "$SCRIPT_DIR/resources/icons/sddm-theme-manager.png" ]; then
    cp "$SCRIPT_DIR/resources/icons/sddm-theme-manager.png" "$ICON_PNG_DIR/"
    chmod 644 "$ICON_PNG_DIR/$APP_NAME.png"
fi

# Update desktop databases if available
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    if [ "$DESKTOP_DIR" != "$HOME/.local/share/applications" ] && [ -d "$HOME/.local/share/applications" ]; then
        update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
    fi
fi
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -q "$SHARE_DIR/icons/hicolor" 2>/dev/null || true
fi
if command -v kbuildsycoca6 &>/dev/null; then
    kbuildsycoca6 --noincremental 2>/dev/null || true
elif command -v kbuildsycoca5 &>/dev/null; then
    kbuildsycoca5 --noincremental 2>/dev/null || true
fi

# Install Polkit Rule (Arch Linux / JavaScript rules)
if [ "$POLKIT_INSTALL" = true ]; then
    if [ "$EUID" -eq 0 ]; then
        echo "Installing Polkit rules to $POLKIT_RULE_FILE..."
        mkdir -p "$POLKIT_RULE_DIR"
        cp "$SCRIPT_DIR/polkit/40-sddm-theme-manager.rules" "$POLKIT_RULE_FILE"
        chown root:root "$POLKIT_RULE_FILE"
        chmod 644 "$POLKIT_RULE_FILE"
        echo "Polkit rule installed with permissions 644 root:root."

        # Restart polkit if running systemd
        if systemctl is-active --quiet polkit 2>/dev/null; then
            echo "Restarting polkit service..."
            systemctl restart polkit || true
        fi
    else
        echo ""
        echo "------------------------------------------------------------------"
        echo "IMPORTANT: Polkit Rule Installation"
        echo "To allow passwordless SDDM restarts and theme operations for"
        echo "members of the wheel group, install the Polkit rule file using:"
        echo ""
        echo "  sudo cp $SCRIPT_DIR/polkit/40-sddm-theme-manager.rules /etc/polkit-1/rules.d/"
        echo "  sudo chown root:root /etc/polkit-1/rules.d/40-sddm-theme-manager.rules"
        echo "  sudo chmod 644 /etc/polkit-1/rules.d/40-sddm-theme-manager.rules"
        echo "  sudo systemctl restart polkit"
        echo "------------------------------------------------------------------"
    fi
fi

echo ""
echo "=============================================="
echo " SDDM Theme Manager installed successfully!"
echo " Launch it via your app launcher or by running:"
echo "   $BIN_DIR/$APP_NAME"
if [ "$MODE" = "user" ] && [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo ""
    echo " 💡 Tip: ~/.local/bin is not currently in your shell PATH."
    echo "    To launch by simply typing '$APP_NAME' in terminal, add it to ~/.bashrc or ~/.zshrc:"
    echo "      export PATH=\"\$HOME/.local/bin:\$PATH\""
fi
echo ""
echo " NOTE: If the app does not appear immediately in your launcher, run:"
echo "   update-desktop-database ~/.local/share/applications/"
echo "=============================================="
