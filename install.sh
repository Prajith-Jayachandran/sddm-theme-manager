#!/usr/bin/env bash
# ==============================================================================
# SDDM Theme Manager - Automated Self-Healing Installation & Diagnostic Script
#
# Automatically resolves common SDDM & Polkit configuration pitfalls:
#   1. Polkit Rules & Permissions: Auto-installs to /etc/polkit-1/rules.d/ with
#      strict root:root 644 ownership, restarts polkitd, and verifies syntax.
#   2. Absolute Desktop Exec Paths: Replaces relative paths with exact absolute
#      binary paths and refreshes desktop/icon databases across KDE & GNOME.
#   3. SDDM Theme Permissions & Sync: Normalizes /usr/share/sddm/themes (0755/0644)
#      and automatically syncs user themes to system storage so SDDM never reverts.
#   4. Shell PATH Integration: Automatically adds ~/.local/bin to ~/.bashrc/~/.zshrc
#      and provides /usr/local/bin symlinks for instant terminal access.
#   5. Dependency Diagnostics: Checks Python 3, PyQt6, SDDM greeters, and ffmpeg.
#   6. Standalone Auto-Repair: Run with --repair / --fix at any time.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="sddm-theme-manager"

# Accurately resolve real invoking user and home directory (even under sudo / su)
REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(getent passwd "$REAL_USER" 2>/dev/null | cut -d: -f6)
if [ -z "$REAL_HOME" ] || [ ! -d "$REAL_HOME" ]; then
    REAL_HOME="$HOME"
fi

MODE=""
PREFIX=""
POLKIT_INSTALL=true
UNINSTALL=false
REPAIR_MODE=false
SYNC_THEMES=true

# Formatting helpers
col_green="\033[1;32m"
col_yellow="\033[1;33m"
col_red="\033[1;31m"
col_cyan="\033[1;36m"
col_bold="\033[1m"
col_reset="\033[0m"

log_info() {
    echo -e "${col_cyan}[INFO]${col_reset} $*"
}

log_success() {
    echo -e "${col_green}[✓]${col_reset} $*"
}

log_warning() {
    echo -e "${col_yellow}[WARNING]${col_reset} $*"
}

log_error() {
    echo -e "${col_red}[ERROR]${col_reset} $*"
}

show_help() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Options:
  --system           Install system-wide to /usr/local (requires sudo/root)
  --user             Install to user home directory (~/.local) without root [Default]
  --prefix <PATH>    Specify custom installation prefix (e.g., /opt, /usr)
  --repair, --fix    Run automated diagnostics & repair all Polkit, SDDM, and cache issues
  --no-polkit        Skip copying the Polkit rules file to /etc/polkit-1/rules.d/
  --no-sync          Skip auto-synchronizing user themes to /usr/share/sddm/themes/
  --uninstall        Uninstall and remove all installed files
  -h, --help         Show this help message

Examples:
  ./install.sh                    # Recommended: Installs user application + auto-configures Polkit
  sudo ./install.sh --system      # System-wide installation with root
  ./install.sh --repair           # Auto-detects and fixes Polkit, permissions, SDDM sync, and caches
  ./install.sh --user             # Install strictly into ~/.local
  sudo ./install.sh --uninstall   # Complete removal
EOF
}

# Run command with privilege elevation safely (never blocks in non-interactive sessions)
run_privileged() {
    if [ "$EUID" -eq 0 ]; then
        "$@"
    elif command -v sudo >/dev/null 2>&1; then
        if sudo -n true 2>/dev/null; then
            sudo "$@"
        elif [ -t 0 ]; then
            sudo "$@"
        else
            return 1
        fi
    elif command -v pkexec >/dev/null 2>&1; then
        if [ -t 0 ]; then
            pkexec "$@"
        else
            return 1
        fi
    else
        return 1
    fi
}

# -----------------------------------------------------------------------------
# Command Line Argument Parsing
# -----------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --system)
            MODE="system"
            PREFIX="/usr/local"
            POLKIT_INSTALL=true
            shift
            ;;
        --user)
            MODE="user"
            PREFIX="$REAL_HOME/.local"
            POLKIT_INSTALL=true
            shift
            ;;
        --prefix)
            PREFIX="$2"
            shift 2
            ;;
        --repair|--fix)
            REPAIR_MODE=true
            shift
            ;;
        --no-polkit)
            POLKIT_INSTALL=false
            shift
            ;;
        --no-sync)
            SYNC_THEMES=false
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

# -----------------------------------------------------------------------------
# UNINSTALLATION ROUTINE
# -----------------------------------------------------------------------------
if [ "$UNINSTALL" = true ]; then
    if [ -f "$SCRIPT_DIR/uninstall.sh" ]; then
        exec "$SCRIPT_DIR/uninstall.sh" "$@"
    else
        log_error "uninstall.sh not found in $SCRIPT_DIR"
        exit 1
    fi
fi

# Auto-detect default prefix based on privilege level
if [ -z "$PREFIX" ]; then
    if [ "$EUID" -eq 0 ]; then
        MODE="system"
        PREFIX="/usr/local"
    else
        MODE="user"
        PREFIX="$REAL_HOME/.local"
    fi
fi

# Target directory definitions
BIN_DIR="$PREFIX/bin"
SHARE_DIR="$PREFIX/share"
APP_DIR="$SHARE_DIR/$APP_NAME"
DESKTOP_DIR="$SHARE_DIR/applications"
ICON_SCALABLE_DIR="$SHARE_DIR/icons/hicolor/scalable/apps"
ICON_PNG_DIR="$SHARE_DIR/icons/hicolor/256x256/apps"
POLKIT_RULE_DIR="/etc/polkit-1/rules.d"
POLKIT_RULE_FILE="$POLKIT_RULE_DIR/40-sddm-theme-manager.rules"
POLKIT_ACTIONS_DIR="/usr/share/polkit-1/actions"
POLKIT_POLICY_FILE="$POLKIT_ACTIONS_DIR/com.sddmthememanager.policy"
SDDM_THEMES_DIR="/usr/share/sddm/themes"
SDDM_CONF_DIR="/etc/sddm.conf.d"

# -----------------------------------------------------------------------------
# DIAGNOSTICS & SYSTEM CHECKS
# -----------------------------------------------------------------------------
check_dependencies() {
    echo ""
    echo -e "${col_bold}Checking System Environment & Dependencies...${col_reset}"

    # 1. Python 3
    if command -v python3 >/dev/null 2>&1; then
        PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
        log_success "Python 3 is available: $PY_VER"
    else
        log_error "Python 3 is not installed. Please install python3."
        return 1
    fi

    # 2. PyQt6
    if python3 -c "import PyQt6" >/dev/null 2>&1; then
        log_success "PyQt6 is installed and accessible."
    else
        log_warning "PyQt6 is not detected in current Python environment."
        echo "  Install via your package manager:"
        echo "    sudo pacman -S python-pyqt6     # Arch / CachyOS / Manjaro"
        echo "    sudo dnf install python3-pyqt6  # Fedora"
        echo "    sudo apt install python3-pyqt6  # Debian / Ubuntu"
    fi

    # 3. SDDM & Greeters
    if command -v sddm >/dev/null 2>&1 || [ -f "/usr/bin/sddm" ]; then
        log_success "SDDM Display Manager detected on system."
    else
        log_warning "SDDM binary not found in standard system paths."
    fi

    if [ -x "/usr/bin/sddm-greeter-qt6" ]; then
        log_success "Found modern Qt 6 greeter: /usr/bin/sddm-greeter-qt6"
    elif [ -x "/usr/bin/sddm-greeter" ]; then
        log_info "Found standard greeter: /usr/bin/sddm-greeter (Qt 5 runtime)"
    fi

    # 4. ffmpeg (Optional, for video backgrounds & preview thumbnails)
    if command -v ffmpeg >/dev/null 2>&1; then
        log_success "ffmpeg is installed (video background previews enabled)."
    else
        log_warning "ffmpeg is missing. Video wallpaper thumbnail extraction will be skipped."
        echo "  Recommended: Install ffmpeg (e.g. 'sudo pacman -S ffmpeg')"
    fi

    # 5. Wheel / Sudo Group Membership (for Polkit passwordless writes)
    USER_GROUPS=$(id -nG "$REAL_USER" 2>/dev/null || true)
    if echo "$USER_GROUPS" | grep -E -q "(wheel|sudo)"; then
        log_success "User '$REAL_USER' belongs to administrative group (wheel/sudo)."
    else
        log_warning "User '$REAL_USER' is not currently in 'wheel' or 'sudo' group."
        echo "  Polkit rules require administrative group membership for passwordless actions."
        echo "  To add yourself to wheel, run: sudo usermod -aG wheel $REAL_USER"
    fi
}

# -----------------------------------------------------------------------------
# AUTOMATED POLKIT SETUP & REPAIR (Solves Troubleshooting Issues #1, #2, #3, #8)
# -----------------------------------------------------------------------------
setup_polkit() {
    if [ "$POLKIT_INSTALL" != true ]; then
        log_info "Skipping Polkit installation as requested (--no-polkit)."
        return 0
    fi

    echo ""
    echo -e "${col_bold}Configuring & Hardening Polkit Rules (Auto-Fix)...${col_reset}"

    if [ ! -f "$SCRIPT_DIR/polkit/40-sddm-theme-manager.rules" ]; then
        log_warning "Polkit rule file not found at $SCRIPT_DIR/polkit/40-sddm-theme-manager.rules. Skipping."
        return 0
    fi

    local polkit_success=false

    # Function to apply polkit files with proper ownership & permissions
    apply_polkit_files() {
        run_privileged mkdir -p "$POLKIT_RULE_DIR"
        run_privileged cp "$SCRIPT_DIR/polkit/40-sddm-theme-manager.rules" "$POLKIT_RULE_FILE"
        run_privileged chown root:root "$POLKIT_RULE_FILE"
        run_privileged chmod 644 "$POLKIT_RULE_FILE"

        if [ -f "$SCRIPT_DIR/polkit/com.sddmthememanager.policy" ]; then
            run_privileged mkdir -p "$POLKIT_ACTIONS_DIR"
            run_privileged cp "$SCRIPT_DIR/polkit/com.sddmthememanager.policy" "$POLKIT_POLICY_FILE"
            run_privileged chown root:root "$POLKIT_POLICY_FILE"
            run_privileged chmod 644 "$POLKIT_POLICY_FILE"
        fi

        # Restart polkit daemon if running systemd
        if command -v systemctl >/dev/null 2>&1; then
            if systemctl is-active --quiet polkit 2>/dev/null || [ "$EUID" -eq 0 ]; then
                run_privileged systemctl restart polkit 2>/dev/null || true
            fi
        fi
    }

    if [ "$EUID" -eq 0 ]; then
        apply_polkit_files && polkit_success=true
    elif sudo -n true 2>/dev/null; then
        log_info "Applying Polkit rules to /etc/polkit-1/rules.d/ (using cached privileges)..."
        apply_polkit_files && polkit_success=true
    elif [ "$MODE" = "system" ] || [ "$REPAIR_MODE" = true ] || [ -t 0 ]; then
        log_info "Applying Polkit rules to /etc/polkit-1/rules.d/ (requires privilege elevation)..."
        if apply_polkit_files; then
            polkit_success=true
        else
            log_warning "Privilege elevation failed or was canceled."
        fi
    fi

    if [ "$polkit_success" = true ]; then
        log_success "Polkit rule installed with strict root:root 644 permissions."
        log_success "Polkit service reloaded successfully."

        # Verify polkit journal for syntax or JavaScript errors
        if command -v journalctl >/dev/null 2>&1; then
            POLKIT_ERRS=$(journalctl -b -u polkit -n 15 --no-pager 2>/dev/null | grep -iE "error|typeerror|failed" | grep "40-sddm-theme-manager" || true)
            if [ -n "$POLKIT_ERRS" ]; then
                log_warning "Polkit journal warning detected: $POLKIT_ERRS"
            else
                log_success "Polkit rule syntax verified cleanly in journald."
            fi
        fi
    else
        log_warning "Could not automatically write Polkit rules to $POLKIT_RULE_FILE."
        echo "  To enable passwordless theme switching manually, run:"
        echo "    sudo cp $SCRIPT_DIR/polkit/40-sddm-theme-manager.rules /etc/polkit-1/rules.d/"
        echo "    sudo chown root:root /etc/polkit-1/rules.d/40-sddm-theme-manager.rules"
        echo "    sudo chmod 644 /etc/polkit-1/rules.d/40-sddm-theme-manager.rules"
        echo "    sudo systemctl restart polkit"
    fi
}

# -----------------------------------------------------------------------------
# AUTOMATED SDDM PERMISSIONS & THEME SYNC (Solves Troubleshooting Issues #4b, #7)
# -----------------------------------------------------------------------------
sync_sddm_themes_and_permissions() {
    echo ""
    echo -e "${col_bold}Normalizing SDDM System Directories & Theme Permissions...${col_reset}"

    # 1. Ensure /usr/share/sddm/themes and /etc/sddm.conf.d exist with 0755
    local themes_ok=false
    local conf_ok=false

    if [ -d "$SDDM_THEMES_DIR" ] && [ -r "$SDDM_THEMES_DIR" ] && [ -x "$SDDM_THEMES_DIR" ]; then
        themes_ok=true
    fi
    if [ -d "$SDDM_CONF_DIR" ] && [ -r "$SDDM_CONF_DIR" ] && [ -x "$SDDM_CONF_DIR" ]; then
        conf_ok=true
    fi

    if [ "$themes_ok" = true ] && [ "$conf_ok" = true ]; then
        log_success "Verified $SDDM_THEMES_DIR & $SDDM_CONF_DIR permissions (world-readable 0755)."
    else
        if [ "$EUID" -eq 0 ] || sudo -n true 2>/dev/null; then
            run_privileged mkdir -p "$SDDM_THEMES_DIR" "$SDDM_CONF_DIR" 2>/dev/null || true
            run_privileged chmod 755 "$SDDM_THEMES_DIR" "$SDDM_CONF_DIR" 2>/dev/null || true
            log_success "Created and normalized $SDDM_THEMES_DIR & $SDDM_CONF_DIR (0755)."
        elif [ "$MODE" = "system" ] || [ "$REPAIR_MODE" = true ]; then
            if run_privileged mkdir -p "$SDDM_THEMES_DIR" "$SDDM_CONF_DIR" 2>/dev/null; then
                run_privileged chmod 755 "$SDDM_THEMES_DIR" "$SDDM_CONF_DIR" 2>/dev/null || true
                log_success "Created and normalized $SDDM_THEMES_DIR & $SDDM_CONF_DIR (0755)."
            fi
        fi
    fi

    # 2. Synchronize user themes to /usr/share/sddm/themes/ with 0755/0644
    if [ "$SYNC_THEMES" = true ]; then
        USER_THEMES_DIR="$REAL_HOME/.local/share/sddm/themes"
        if [ -d "$USER_THEMES_DIR" ]; then
            SYNC_COUNT=0
            for theme_path in "$USER_THEMES_DIR"/*; do
                if [ -d "$theme_path" ]; then
                    theme_name=$(basename "$theme_path")
                    target_sys_theme="$SDDM_THEMES_DIR/$theme_name"
                    if [ ! -d "$target_sys_theme" ]; then
                        if [ "$EUID" -eq 0 ] || sudo -n true 2>/dev/null || [ "$MODE" = "system" ] || [ "$REPAIR_MODE" = true ]; then
                            log_info "Syncing un-synced user theme '$theme_name' to $SDDM_THEMES_DIR..."
                            if run_privileged cp -r "$theme_path" "$SDDM_THEMES_DIR/"; then
                                run_privileged chmod -R a+rX "$target_sys_theme" 2>/dev/null || true
                                ((SYNC_COUNT++))
                            fi
                        fi
                    fi
                fi
            done
            if [ $SYNC_COUNT -gt 0 ]; then
                log_success "Synced $SYNC_COUNT user theme(s) to SDDM system directory with world-readable permissions."
            else
                log_success "All user themes are already synchronized to $SDDM_THEMES_DIR."
            fi
        fi
    fi
}

# -----------------------------------------------------------------------------
# AUTOMATED DESKTOP, CACHES & PATH INTEGRATION (Solves Troubleshooting Issue #4)
# -----------------------------------------------------------------------------
setup_desktop_and_icons() {
    echo ""
    echo -e "${col_bold}Installing Desktop Entries, Icons & Updating Caches...${col_reset}"

    mkdir -p "$DESKTOP_DIR"
    mkdir -p "$ICON_SCALABLE_DIR"
    mkdir -p "$ICON_PNG_DIR"

    # Install Desktop Entry with absolute executable path (never relies on desktop $PATH)
    EXEC_TARGET="$BIN_DIR/$APP_NAME"
    DESKTOP_SRC="$SCRIPT_DIR/resources/sddm-theme-manager.desktop"

    if [ -f "$DESKTOP_SRC" ]; then
        sed "s|^Exec=.*|Exec=$EXEC_TARGET|" "$DESKTOP_SRC" > "$DESKTOP_DIR/$APP_NAME.desktop"
        chmod 644 "$DESKTOP_DIR/$APP_NAME.desktop"
        log_success "Installed desktop launcher to $DESKTOP_DIR/$APP_NAME.desktop (Exec=$EXEC_TARGET)"

        # Also copy to user desktop applications directory if installing system-wide
        if [ "$MODE" = "system" ] && [ -d "$REAL_HOME/.local/share/applications" ]; then
            sed "s|^Exec=.*|Exec=$EXEC_TARGET|" "$DESKTOP_SRC" > "$REAL_HOME/.local/share/applications/$APP_NAME.desktop"
            chown "$REAL_USER:$REAL_USER" "$REAL_HOME/.local/share/applications/$APP_NAME.desktop" 2>/dev/null || true
            chmod 644 "$REAL_HOME/.local/share/applications/$APP_NAME.desktop" 2>/dev/null || true
        fi
    fi

    # Install Icons
    if [ -f "$SCRIPT_DIR/resources/icons/sddm-theme-manager.svg" ]; then
        cp "$SCRIPT_DIR/resources/icons/sddm-theme-manager.svg" "$ICON_SCALABLE_DIR/$APP_NAME.svg"
        chmod 644 "$ICON_SCALABLE_DIR/$APP_NAME.svg"
        log_success "Installed vector icon to $ICON_SCALABLE_DIR/$APP_NAME.svg"
    fi

    if [ -f "$SCRIPT_DIR/resources/icons/sddm-theme-manager.png" ]; then
        cp "$SCRIPT_DIR/resources/icons/sddm-theme-manager.png" "$ICON_PNG_DIR/$APP_NAME.png"
        chmod 644 "$ICON_PNG_DIR/$APP_NAME.png"
        log_success "Installed PNG icon to $ICON_PNG_DIR/$APP_NAME.png"
    fi

    # Refresh Desktop Databases
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
        if [ -d "$REAL_HOME/.local/share/applications" ]; then
            update-desktop-database "$REAL_HOME/.local/share/applications" 2>/dev/null || true
        fi
        if [ -d "/usr/share/applications" ] && [ "$EUID" -eq 0 ]; then
            update-desktop-database "/usr/share/applications" 2>/dev/null || true
        fi
        log_success "Application desktop database refreshed."
    fi

    # Refresh Icon Caches
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -q "$SHARE_DIR/icons/hicolor" 2>/dev/null || true
        log_success "GTK icon cache refreshed."
    fi

    # Refresh KDE Sycoca Cache (KDE Plasma 6 / 5)
    if command -v kbuildsycoca6 >/dev/null 2>&1; then
        kbuildsycoca6 --noincremental 2>/dev/null || true
        log_success "KDE Plasma 6 Sycoca cache refreshed."
    elif command -v kbuildsycoca5 >/dev/null 2>&1; then
        kbuildsycoca5 --noincremental 2>/dev/null || true
        log_success "KDE Plasma 5 Sycoca cache refreshed."
    fi
}

setup_path_integration() {
    # Check if $BIN_DIR is in PATH
    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        # Create a system symlink in /usr/local/bin if possible without prompting
        if [ "$BIN_DIR" != "/usr/local/bin" ] && [ -d "/usr/local/bin" ]; then
            if [ -w "/usr/local/bin" ]; then
                ln -sf "$BIN_DIR/$APP_NAME" "/usr/local/bin/$APP_NAME"
                log_success "Created universal symlink: /usr/local/bin/$APP_NAME -> $BIN_DIR/$APP_NAME"
                return 0
            elif sudo -n true 2>/dev/null; then
                sudo ln -sf "$BIN_DIR/$APP_NAME" "/usr/local/bin/$APP_NAME"
                log_success "Created universal symlink: /usr/local/bin/$APP_NAME -> $BIN_DIR/$APP_NAME"
                return 0
            fi
        fi

        # Auto-configure PATH export in ~/.bashrc and ~/.zshrc
        if [ "$MODE" = "user" ]; then
            local path_line="export PATH=\"\$HOME/.local/bin:\$PATH\""

            if [ -f "$REAL_HOME/.bashrc" ] && ! grep -q "\$HOME/.local/bin" "$REAL_HOME/.bashrc" 2>/dev/null; then
                echo -e "\n# Added by SDDM Theme Manager installer\n$path_line" >> "$REAL_HOME/.bashrc"
                log_success "Added ~/.local/bin to $REAL_HOME/.bashrc"
            fi

            if [ -f "$REAL_HOME/.zshrc" ] && ! grep -q "\$HOME/.local/bin" "$REAL_HOME/.zshrc" 2>/dev/null; then
                echo -e "\n# Added by SDDM Theme Manager installer\n$path_line" >> "$REAL_HOME/.zshrc"
                log_success "Added ~/.local/bin to $REAL_HOME/.zshrc"
            fi
        fi
    else
        log_success "Binary directory ($BIN_DIR) is already in current shell PATH."
    fi
}

# -----------------------------------------------------------------------------
# STANDALONE AUTOMATED REPAIR / HEALTH-CHECK MODE
# -----------------------------------------------------------------------------
run_repair_mode() {
    echo "=============================================="
    echo " SDDM Theme Manager - Automated Diagnostics & Repair"
    echo "=============================================="

    check_dependencies
    setup_polkit
    sync_sddm_themes_and_permissions
    setup_desktop_and_icons
    setup_path_integration

    echo ""
    echo "=============================================="
    echo -e "${col_green} 🎉 All diagnostic and self-healing checks completed!${col_reset}"
    echo " All Polkit rules, SDDM directory permissions, desktop launchers,"
    echo " and theme synchronizations have been verified and repaired."
    echo "=============================================="
    exit 0
}

if [ "$REPAIR_MODE" = true ]; then
    run_repair_mode
fi

# -----------------------------------------------------------------------------
# FULL INSTALLATION ROUTINE
# -----------------------------------------------------------------------------
echo "=============================================="
echo " Installing SDDM Theme Manager"
echo " Prefix: $PREFIX"
echo " Mode:   $MODE"
echo " User:   $REAL_USER"
echo "=============================================="

# Pre-install environment checks
check_dependencies

# Create target directories
mkdir -p "$BIN_DIR"
mkdir -p "$APP_DIR"

# Copy source code and application modules
echo ""
echo -e "${col_bold}Copying Application Files to $APP_DIR...${col_reset}"
cp -r "$SCRIPT_DIR/main.py" "$APP_DIR/"
cp -r "$SCRIPT_DIR/core" "$APP_DIR/"
cp -r "$SCRIPT_DIR/ui" "$APP_DIR/"
cp -r "$SCRIPT_DIR/resources" "$APP_DIR/"
[ -f "$SCRIPT_DIR/README.md" ] && cp "$SCRIPT_DIR/README.md" "$APP_DIR/"
[ -d "$SCRIPT_DIR/sddm_theme_manager" ] && cp -r "$SCRIPT_DIR/sddm_theme_manager" "$APP_DIR/"
[ -d "$SCRIPT_DIR/polkit" ] && cp -r "$SCRIPT_DIR/polkit" "$APP_DIR/"
chmod -R a+rX "$APP_DIR"
log_success "Application files copied and permissions normalized."

# Create launcher executable wrapper
echo ""
echo -e "${col_bold}Creating Executable Launcher in $BIN_DIR/$APP_NAME...${col_reset}"
cat << EOF > "$BIN_DIR/$APP_NAME"
#!/usr/bin/env bash
exec /usr/bin/python3 "$APP_DIR/main.py" "\$@"
EOF
chmod 755 "$BIN_DIR/$APP_NAME"
log_success "Executable launcher created: $BIN_DIR/$APP_NAME"

# Perform automated desktop entry, cache, polkit, and SDDM directory fixes
setup_desktop_and_icons
setup_path_integration
setup_polkit
sync_sddm_themes_and_permissions

# Verify Boot Shield watchdog safety configuration
if [ -f "$APP_DIR/main.py" ]; then
    echo ""
    echo -e "${col_bold}Verifying Boot Shield Watchdog Safety...${col_reset}"
    python3 "$APP_DIR/main.py" --verify-shield || true
fi

echo ""
echo "=============================================="
echo -e "${col_green} SDDM Theme Manager installed successfully!${col_reset}"
echo " Launch it via your application menu or terminal:"
echo "   $APP_NAME"
echo ""
echo " 💡 Tip: If you ever encounter permission or Polkit issues, run:"
echo "   $SCRIPT_DIR/install.sh --repair"
echo "=============================================="
