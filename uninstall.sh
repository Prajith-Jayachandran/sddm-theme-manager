#!/usr/bin/env bash
# ==============================================================================
# SDDM Theme Manager - Uninstallation Script
# Removes all installed binaries, application files, desktop entries, icons,
# and Polkit rules from both user (~/.local) and system (/usr/local) locations.
# Automatically elevates privileges with sudo when system components exist.
# ==============================================================================

set -e

APP_NAME="sddm-theme-manager"
AUTO_CONFIRM=false
TARGET_PREFIX=""
ONLY_USER=false
ONLY_SYSTEM=false

show_help() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Options:
  --user             Remove only user-level installation (~/.local, no sudo required)
  --system           Remove only system-wide installation (/usr/local, requires sudo)
  --prefix <PATH>    Remove from a custom installation prefix
  -y, --yes          Bypass confirmation prompt
  -h, --help         Show this help message

Examples:
  ./uninstall.sh           # Auto-detects, requests sudo privileges if needed, and removes all installed files
  ./uninstall.sh -y        # Uninstalls silently without interactive confirmation
  ./uninstall.sh --user    # Removes only user-level installation without root
  sudo ./uninstall.sh      # Completely removes system files and Polkit rules
EOF
}

# -----------------------------------------------------------------------------
# 1. Parse Arguments First
# -----------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --user)
            ONLY_USER=true
            TARGET_PREFIX="$HOME/.local"
            shift
            ;;
        --system)
            ONLY_SYSTEM=true
            TARGET_PREFIX="/usr/local"
            shift
            ;;
        --prefix)
            TARGET_PREFIX="$2"
            shift 2
            ;;
        -y|--yes)
            AUTO_CONFIRM=true
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

# -----------------------------------------------------------------------------
# 2. Privilege Escalation (Sudo)
# -----------------------------------------------------------------------------
# System-wide components and Polkit rules require root/sudo privileges.
# Automatically elevate using sudo if not running as root and not user-only mode.
if [ "$ONLY_USER" = false ] && [ "$EUID" -ne 0 ]; then
    echo "=============================================="
    echo " SDDM Theme Manager - Uninstaller"
    echo "=============================================="
    echo "Uninstallation requires sudo privileges to remove system files and Polkit rules."
    
    if command -v sudo >/dev/null 2>&1; then
        echo "Elevating privileges with sudo..."
        exec sudo "$0" "$@"
    elif command -v pkexec >/dev/null 2>&1; then
        echo "Elevating privileges with pkexec..."
        exec pkexec "$0" "$@"
    else
        echo "Error: Neither sudo nor pkexec was found."
        echo "Please run this script directly with root privileges: sudo $0 $*"
        exit 1
    fi
fi

echo "=============================================="
echo " SDDM Theme Manager - Uninstaller"
echo "=============================================="

# -----------------------------------------------------------------------------
# 3. Determine Search Prefixes
# -----------------------------------------------------------------------------
PREFIXES=()

if [ -n "$TARGET_PREFIX" ]; then
    PREFIXES+=("$TARGET_PREFIX")
else
    # Auto-detect mode: scan user homes and system locations
    # Resolve invoking user's home directory even when running under sudo
    REAL_USER="${SUDO_USER:-$USER}"
    REAL_HOME=$(getent passwd "$REAL_USER" 2>/dev/null | cut -d: -f6)
    if [ -n "$REAL_HOME" ] && [ -d "$REAL_HOME" ]; then
        PREFIXES+=("$REAL_HOME/.local")
    elif [ -n "$HOME" ] && [ -d "$HOME" ]; then
        PREFIXES+=("$HOME/.local")
    fi

    # Include root .local only if distinct
    if [ -n "$HOME" ] && [ "$HOME" != "$REAL_HOME" ] && [ -d "$HOME/.local" ]; then
        PREFIXES+=("$HOME/.local")
    fi

    if [ "$ONLY_USER" = false ]; then
        PREFIXES+=("/usr/local")
        PREFIXES+=("/usr")
    fi
fi

# -----------------------------------------------------------------------------
# 4. Detect Installed Files
# -----------------------------------------------------------------------------
FOUND_ITEMS=()

for PFX in "${PREFIXES[@]}"; do
    [ -f "$PFX/bin/$APP_NAME" ] && FOUND_ITEMS+=("$PFX/bin/$APP_NAME")
    [ -d "$PFX/share/$APP_NAME" ] && FOUND_ITEMS+=("$PFX/share/$APP_NAME")
    [ -f "$PFX/share/applications/$APP_NAME.desktop" ] && FOUND_ITEMS+=("$PFX/share/applications/$APP_NAME.desktop")
    [ -f "$PFX/share/icons/hicolor/scalable/apps/$APP_NAME.svg" ] && FOUND_ITEMS+=("$PFX/share/icons/hicolor/scalable/apps/$APP_NAME.svg")
    [ -f "$PFX/share/icons/hicolor/256x256/apps/$APP_NAME.png" ] && FOUND_ITEMS+=("$PFX/share/icons/hicolor/256x256/apps/$APP_NAME.png")
done

POLKIT_RULE="/etc/polkit-1/rules.d/40-sddm-theme-manager.rules"
if [ "$ONLY_USER" = false ] && [ -f "$POLKIT_RULE" ]; then
    FOUND_ITEMS+=("$POLKIT_RULE")
fi

if [ ${#FOUND_ITEMS[@]} -eq 0 ]; then
    echo "No installed files for SDDM Theme Manager were found."
    exit 0
fi

echo "The following installed items were detected:"
for item in "${FOUND_ITEMS[@]}"; do
    echo "  • $item"
done
echo ""

# -----------------------------------------------------------------------------
# 5. Confirm Removal
# -----------------------------------------------------------------------------
if [ "$AUTO_CONFIRM" = false ]; then
    if [ -t 0 ]; then
        read -rp "Are you sure you want to completely remove these files? [y/N]: " CONFIRM
        case "$CONFIRM" in
            [yY]|[yY][eE][sS])
                ;;
            *)
                echo "Uninstallation cancelled."
                exit 0
                ;;
        esac
    else
        echo "Running non-interactively without -y. Proceeding with removal..."
    fi
fi

echo ""
echo "Removing files..."

DESKTOP_DIRS_TO_UPDATE=()
ICON_DIRS_TO_UPDATE=()

for PFX in "${PREFIXES[@]}"; do
    # Remove launcher binary
    if [ -f "$PFX/bin/$APP_NAME" ]; then
        if rm -f "$PFX/bin/$APP_NAME"; then
            echo "  ✓ Removed: $PFX/bin/$APP_NAME"
        else
            echo "  ❌ Failed to remove: $PFX/bin/$APP_NAME"
        fi
    fi

    # Remove application directory
    if [ -d "$PFX/share/$APP_NAME" ]; then
        if rm -rf "$PFX/share/$APP_NAME"; then
            echo "  ✓ Removed directory: $PFX/share/$APP_NAME"
        else
            echo "  ❌ Failed to remove directory: $PFX/share/$APP_NAME"
        fi
    fi

    # Remove desktop shortcut
    if [ -f "$PFX/share/applications/$APP_NAME.desktop" ]; then
        if rm -f "$PFX/share/applications/$APP_NAME.desktop"; then
            echo "  ✓ Removed: $PFX/share/applications/$APP_NAME.desktop"
            DESKTOP_DIRS_TO_UPDATE+=("$PFX/share/applications")
        else
            echo "  ❌ Failed to remove: $PFX/share/applications/$APP_NAME.desktop"
        fi
    fi

    # Remove icons
    if [ -f "$PFX/share/icons/hicolor/scalable/apps/$APP_NAME.svg" ]; then
        if rm -f "$PFX/share/icons/hicolor/scalable/apps/$APP_NAME.svg"; then
            echo "  ✓ Removed icon: $PFX/share/icons/hicolor/scalable/apps/$APP_NAME.svg"
            ICON_DIRS_TO_UPDATE+=("$PFX/share/icons/hicolor")
        fi
    fi

    if [ -f "$PFX/share/icons/hicolor/256x256/apps/$APP_NAME.png" ]; then
        if rm -f "$PFX/share/icons/hicolor/256x256/apps/$APP_NAME.png"; then
            echo "  ✓ Removed icon: $PFX/share/icons/hicolor/256x256/apps/$APP_NAME.png"
            ICON_DIRS_TO_UPDATE+=("$PFX/share/icons/hicolor")
        fi
    fi
done

# Remove Polkit rule
if [ "$ONLY_USER" = false ] && [ -f "$POLKIT_RULE" ]; then
    if [ "$EUID" -eq 0 ]; then
        rm -f "$POLKIT_RULE"
        echo "  ✓ Removed Polkit rule: $POLKIT_RULE"
        if systemctl is-active --quiet polkit 2>/dev/null; then
            systemctl restart polkit || true
            echo "  ✓ Reloaded Polkit daemon."
        fi
    else
        echo "  ⚠ Polkit rule requires root to remove: $POLKIT_RULE"
    fi
fi

# -----------------------------------------------------------------------------
# 6. Update System Caches
# -----------------------------------------------------------------------------
echo "Updating desktop and icon caches..."

for d_dir in "${DESKTOP_DIRS_TO_UPDATE[@]}"; do
    if [ -d "$d_dir" ] && command -v update-desktop-database &>/dev/null; then
        update-desktop-database "$d_dir" 2>/dev/null || true
    fi
done

# Always ensure user's applications database is updated
USER_DESKTOP_DIR="${REAL_HOME:-$HOME}/.local/share/applications"
if [ -d "$USER_DESKTOP_DIR" ] && command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$USER_DESKTOP_DIR" 2>/dev/null || true
fi

for i_dir in "${ICON_DIRS_TO_UPDATE[@]}"; do
    if [ -d "$i_dir" ] && command -v gtk-update-icon-cache &>/dev/null; then
        gtk-update-icon-cache -q "$i_dir" 2>/dev/null || true
    fi
done

if command -v kbuildsycoca6 &>/dev/null; then
    kbuildsycoca6 --noincremental 2>/dev/null || true
elif command -v kbuildsycoca5 &>/dev/null; then
    kbuildsycoca5 --noincremental 2>/dev/null || true
fi

echo ""
echo "=============================================="
echo " SDDM Theme Manager successfully uninstalled."
echo ""
echo " NOTE: Make sure to refresh your desktop application database:"
echo "   update-desktop-database ~/.local/share/applications/"
echo "=============================================="
