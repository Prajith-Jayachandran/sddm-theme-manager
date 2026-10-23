# SDDM Theme Manager

A standalone, desktop-environment-agnostic GUI application for managing and customizing [SDDM](https://github.com/sddm/sddm) (Simple Desktop Display Manager) themes.

Works identically on **KDE Plasma**, **GNOME**, **Hyprland**, and other window managers / desktop environments without being tied to any specific desktop ecosystem or control center.

---

## ✨ Features

- **Theme Browser & Real-Time Filesystem Watcher**:
  - Automatically scans `/usr/share/sddm/themes/`, `/usr/local/share/sddm/themes/`, and `~/.local/share/sddm/themes/`.
  - Built-in `QFileSystemWatcher` live-tracks directory changes and refreshes the UI automatically without manual reload.
  - Discovers previews across non-standard filenames (`preview.*`, `screenshot.*`), subdirectories (`screenshots/`, `images/`, `backgrounds/`, `assets/`), and extracts video background frames (`.mp4`, `.webm`) via `ffmpeg`.
  - Dynamic fallback thumbnail generator: guarantees every theme has an attractive visual preview card.
  - Real-time search and filter by name, Qt version (Qt 6 / Qt 5), and installation date.

- **Direct-to-System Installation & Complete 1-Click Removal**:
  - **Direct System Storage**: All theme downloads (KDE Store) and archive installs (`.tar.gz`, `.zip`) install straight into `/usr/share/sddm/themes/` with permissions normalized (`0755` directories, `0644` files) via Polkit (`pkexec`).
  - **Unified Complete Deletion**: Deleting any theme permanently wipes the system directory in `/usr/share/sddm/themes/` and purges any legacy copy in `~/.local/share/sddm/themes/` simultaneously.

- **🎨 Desktop Synchronization & Ricing Tools**:
  - **Match Desktop Wallpaper**: 1-click sync that automatically detects your active desktop wallpaper from **KDE Plasma**, **Hyprland** (`swww`/`hyprpaper`), **GNOME**, **Sway**, **Feh**, **Nitrogen**, or **XFCE** and sets it as the SDDM background.
  - **Dynamic Palette & Pywal Accent Colors**: Samples dominant and accent colors from wallpapers using native `QImage` pixel analysis, and imports color schemes directly from Pywal (`~/.cache/wal/colors.json`).
  - **Animated & Video Wallpapers**: Full support for `.mp4`, `.webm`, `.mkv`, and `.gif` animated backgrounds with automatic static poster frame generation for card thumbnails and greeter fallbacks.

- **⚙️ Visual Theme Customizer (Theme Tweaker)**:
  - Intuitive dialog to configure `theme.conf.user` parameters without touching raw text files:
    - **Clock & Time**: 12-hour vs 24-hour format, toggle seconds, show/hide clock.
    - **Layout Alignment**: Center, left, or right login box positioning.
    - **Visual Effects**: Background blur radius slider (0–50px) and dim opacity slider (0–80%).
    - **Typography**: Custom font family picker and base font size spinbox.
    - **Color Overrides**: Interactive accent color picker.

- **👤 User Profile Avatar Manager**:
  - Select, preview, and apply circular user login avatars.
  - Automatically provisions both legacy `~/.face.icon` and modern AccountsService (`/var/lib/AccountsService/icons/<user>` and `/var/lib/AccountsService/users/<user>`).

- **🌓 Day / Night Theme Scheduler**:
  - Automatically transitions between a light theme in the daytime and a dark theme in the evening.
  - Backed by an automated background systemd user timer (`sddm-theme-scheduler.timer`).
  - Supports headless execution via `sddm-theme-manager --apply-scheduled`.

- **🛡️ Qt5 vs Qt6 Compatibility Linter & Auto-Patcher**:
  - Scans QML files in downloaded themes to prevent black screens and crashes on modern Qt6 greeters.
  - Flags legacy imports (e.g. `QtGraphicalEffects 1.0`) and recommends missing Arch Linux runtime packages (e.g. `qt6-5compat`).
  - 1-click **"🛡️ Auto-Patch for Qt 6"** button upgrades imports to `Qt5Compat.GraphicalEffects 6.0` and creates safety `.qml.bak` backups.

- **📦 1-Click Theme Backup, Export & Sharing**:
  - Bundles any customized theme, custom background, user overrides, and a `manifest.json` into a shareable `.tar.gz` or `.tar.zst` archive for community sharing.
  - Seamless 1-click import that extracts and registers shared bundles.

- **🖥️ Multi-Monitor Display Setup**:
  - Discovers all connected displays (e.g., `eDP-1`, `DP-1`, `HDMI-A-1`) via `xrandr` and DRM sysfs.
  - Configures the primary screen in `/usr/share/sddm/scripts/Xsetup` so the SDDM login box always appears on the intended display.

- **🎛️ SDDM Daemon Control Panel (Autologin & Sessions)**:
  - Discovers installed Wayland and X11 sessions (e.g. `Hyprland`, `Plasma`).
  - Configures autologin user, autologin session, and relogin behavior in `/etc/sddm.conf.d/20-autologin.conf`.
  - Manages boot NumLock state (`none`, `on`, `off`) and user persistence in `/etc/sddm.conf.d/00-general.conf`.

- **Wayland-Compatible Live Greeter Preview**:
  - Launches `sddm-greeter-qt6 --test-mode --theme <path>` (or `sddm-greeter` for Qt 5) in a non-blocking subprocess.
  - Floating top-center exit overlay with periodic re-raise to ensure visibility over full-screen greeters on Wayland (KWin) and X11.
  - In-app emergency top banner with instant `[ ✕ Stop Live Preview ]` button and global `Esc` shortcut.
  - Does **not** require root privileges for preview rendering.

---

## 🚀 Quick Start

### 1. Requirements

Before running or installing SDDM Theme Manager, ensure the following core dependencies are installed on your system:

| Dependency | Minimum Version | Purpose |
|:---|:---|:---|
| **Python** | `3.11+` | Application runtime |
| **PySide6** | `6.5+` | Qt 6 GUI framework and rendering engine |
| **SDDM** | `0.20+` | Display manager daemon and greeter (`sddm-greeter-qt6` or `sddm-greeter`) |
| **Polkit** | Any | Elevated privilege execution (`pkexec`) for config writes and service restarts |
| **Systemd** | Any | SDDM service management (`systemctl restart sddm`) |
| **ffmpeg** *(Optional)* | Any | Automatic video thumbnail extraction for animated `.mp4`/`.webm` themes |
| **desktop-file-utils** *(Optional)* | Any | Provides `update-desktop-database` to refresh desktop application menus |

---

### 📦 Dependency Installation by Distribution

#### **Arch Linux / CachyOS / Manjaro / EndeavourOS**
```bash
sudo pacman -S --needed python pyside6 sddm polkit systemd ffmpeg desktop-file-utils
```

#### **Fedora / RHEL 9+**
```bash
sudo dnf install python3 python3-pyside6 sddm polkit systemd ffmpeg desktop-file-utils
```

#### **Debian / Ubuntu 24.04+ / Linux Mint / Pop!_OS**
```bash
sudo apt update
sudo apt install python3 python3-pip sddm polkitd pkexec systemd ffmpeg desktop-file-utils
sudo apt install python3-pyside6.qtwidgets python3-pyside6.qtgui python3-pyside6.qtcore
```

#### **openSUSE (Tumbleweed / Leap)**
```bash
sudo zypper install python3 python3-pyside6 sddm polkit systemd ffmpeg desktop-file-utils
```

#### **Alternative: Install PySide6 via `pip`**
If your distribution does not include `python-pyside6` in its package manager, install PySide6 directly via `pip`:
```bash
python3 -m pip install --user PySide6
```

---

### 🔍 Verification Commands

You can verify that all prerequisites are correctly installed by running:

```bash
# 1. Check Python version (requires 3.11+)
python3 --version

# 2. Check PySide6 (Qt 6) installation
python3 -c "import PySide6; print('PySide6 version:', PySide6.__version__)"

# 3. Check SDDM and greeter binary
sddm --version
which sddm-greeter-qt6 || which sddm-greeter

# 4. Check Polkit (pkexec)
pkexec --version

# 5. Check Systemd
systemctl --version

# 6. Check desktop database tool
update-desktop-database --version
```

---

## 📦 Installation

Run the included `install.sh` script:

### System-wide Installation (Recommended)
```bash
cd ~/sddm-theme-manager
sudo ./install.sh
```
This installs:
- Executable: `/usr/local/bin/sddm-theme-manager`
- Application code & assets: `/usr/local/share/sddm-theme-manager/`
- Desktop entry: `/usr/local/share/applications/sddm-theme-manager.desktop`
- Scalable & PNG icons: `/usr/local/share/icons/hicolor/...`
- Polkit rules: `/etc/polkit-1/rules.d/40-sddm-theme-manager.rules`

### User-Level Installation (No Root)
```bash
cd ~/sddm-theme-manager
./install.sh --user
```
Installs to `~/.local/bin` and `~/.local/share/applications`.

> [!IMPORTANT]
> **Refresh Desktop Application Database**:
> After installing (or uninstalling), make sure to run:
> ```bash
> update-desktop-database ~/.local/share/applications/
> ```
> *(Or `sudo update-desktop-database /usr/local/share/applications/` for system-wide installs).*
> This immediately updates your desktop launcher index (KDE Plasma, GNOME, XFCE, Hyprland, rofi, wofi) so the application icon shows up without needing to log out or reboot.

---

## 🗑️ Uninstallation

To remove SDDM Theme Manager and all its installed files, run the included `uninstall.sh` script:

```bash
cd ~/sddm-theme-manager
./uninstall.sh
```

> [!NOTE]
> `uninstall.sh` automatically elevates privileges with `sudo` when system files (`/usr/local/`) or Polkit rules (`/etc/polkit-1/rules.d/`) need to be removed. It also resolves the original user's home directory so both system and user-level installations are cleanly removed in a single run.

> [!IMPORTANT]
> **Refresh Desktop Application Database**:
> After uninstalling, make sure to refresh your desktop application database:
> ```bash
> update-desktop-database ~/.local/share/applications/
> ```
> This ensures that the application shortcut is immediately purged from your application menus and search bars.

### Options:
- **Automatic removal (prompts for sudo if system files exist)**:
  ```bash
  ./uninstall.sh
  ```
- **Silent uninstallation (no interactive confirmation)**:
  ```bash
  ./uninstall.sh -y
  ```
- **User-only uninstallation (no sudo required)**:
  ```bash
  ./uninstall.sh --user
  ```
- **Explicit system removal with sudo**:
  ```bash
  sudo ./uninstall.sh
  ```
- **Via install script**:
  ```bash
  ./install.sh --uninstall
  ```

---

## 🔒 Polkit Configuration (Arch Linux)

Arch Linux uses JavaScript-based `.rules` files in `/etc/polkit-1/rules.d/`.

### Installing the Rule File

Copy `polkit/40-sddm-theme-manager.rules` into the Polkit directory:

```bash
sudo cp ~/sddm-theme-manager/polkit/40-sddm-theme-manager.rules /etc/polkit-1/rules.d/
sudo chown root:root /etc/polkit-1/rules.d/40-sddm-theme-manager.rules
sudo chmod 644 /etc/polkit-1/rules.d/40-sddm-theme-manager.rules
sudo systemctl restart polkit
```

> [!IMPORTANT]
> **Permissions Pitfall**: The file **must** be owned by `root:root` with permissions `644` (or `640` with group `polkitd`). If permissions are incorrect, `polkitd` will silently ignore the file.

### Verify Polkit Rule Loading

Check the system journal to verify that the rule loaded without errors:
```bash
sudo ls -la /etc/polkit-1/rules.d/40-sddm-theme-manager.rules
journalctl -b -u polkit | grep -E "Error loading|40-sddm-theme-manager"
```

---

## ⚠️ Troubleshooting & Error Resolution

### 1. `Failed to write configuration: Error executing command as another user: Not authorized`
- **Cause**: Either the Polkit rule is not installed in `/etc/polkit-1/rules.d/`, or an older rule using `action.lookup("argv")` caused a JavaScript `TypeError` in `polkitd` because Polkit provides `action.lookup("command_line")` instead of an array.
- **Resolution**: Copy the updated rule file and restart Polkit:
  ```bash
  sudo cp ~/sddm-theme-manager/polkit/40-sddm-theme-manager.rules /etc/polkit-1/rules.d/
  sudo chown root:root /etc/polkit-1/rules.d/40-sddm-theme-manager.rules
  sudo chmod 644 /etc/polkit-1/rules.d/40-sddm-theme-manager.rules
  sudo systemctl restart polkit
  ```

### 2. `cp: cannot stat '/root/sddm-theme-manager/...': No such file or directory`
- **Cause**: If you switched to a root shell (`sudo su`), `~` resolves to `/root/` instead of your user's home directory (`/home/<user>/`).
- **Resolution**: Use the explicit path from your user directory:
  ```bash
  cp /home/$USER/sddm-theme-manager/polkit/40-sddm-theme-manager.rules /etc/polkit-1/rules.d/
  chown root:root /etc/polkit-1/rules.d/40-sddm-theme-manager.rules
  chmod 644 /etc/polkit-1/rules.d/40-sddm-theme-manager.rules
  systemctl restart polkit
  ```

### 3. `Permission denied` when copying to `/etc/polkit-1/rules.d/`
- **Cause**: The `/etc/polkit-1/rules.d/` directory has strict `700` (`rwx------`) permissions owned by `root`. Standard user shells cannot view or write files there without privilege elevation.
- **Resolution**: Always prefix copy, chown, and chmod commands with `sudo`:
  ```bash
  sudo cp ~/sddm-theme-manager/polkit/40-sddm-theme-manager.rules /etc/polkit-1/rules.d/
  sudo chown root:root /etc/polkit-1/rules.d/40-sddm-theme-manager.rules
  sudo chmod 644 /etc/polkit-1/rules.d/40-sddm-theme-manager.rules
  sudo systemctl restart polkit
  ```

### 4. `Launching SDDM Theme Manager (Failed): Could not find the program 'sddm-theme-manager'`
- **Cause**: On Linux desktop environments (such as KDE Plasma or GNOME), desktop shortcuts with relative command paths (`Exec=sddm-theme-manager`) rely on the desktop session's `$PATH`. User binary directories like `~/.local/bin` are frequently not in the desktop session's `$PATH` by default.
- **Resolution**:
  - `install.sh` automatically writes the absolute executable path into the desktop entry (e.g., `Exec=/home/<user>/.local/bin/sddm-theme-manager` or `Exec=/usr/local/bin/sddm-theme-manager`).
  - Re-run the installer:
    ```bash
    cd ~/sddm-theme-manager
    ./install.sh --user
    ```
  - Refresh your application database:
    ```bash
    update-desktop-database ~/.local/share/applications/
    kbuildsycoca6 --noincremental   # For KDE Plasma
    ```

### 4. Applied Theme Does Not Show in SDDM (Reverts to Default Breeze)
- **Cause**: SDDM runs as a dedicated system user (`sddm`, UID 952). The SDDM daemon reads `Current=<theme-name>` from `/etc/sddm.conf.d/10-theme.conf` and searches for the theme in `/usr/share/sddm/themes/`. If a theme only exists in user storage (`~/.local/share/sddm/themes/`), SDDM cannot access it because Linux user home directories usually have mode `700` (`drwx------`). When SDDM fails to locate or read the theme directory, it silently falls back to the default `breeze` theme.
- **Resolution**:
  - **In-App (1-Click)**: Click the **"⚡ Fix & Sync to SDDM Now"** button in the health alert banner, or select the theme and click **"Sync to SDDM"** in the details panel.
  - **Automated Sync**: SDDM Theme Manager automatically syncs newly applied or downloaded themes to `/usr/share/sddm/themes/` with normalized world-readable permissions (`0755` dirs, `0644` files).
  - **Manual CLI**:
    ```bash
    sudo cp -r ~/.local/share/sddm/themes/<theme-name> /usr/share/sddm/themes/
    sudo chmod -R a+rX /usr/share/sddm/themes/<theme-name>
    ```

### 5. Cannot Exit Full-Screen Live Greeter Preview (Wayland / KWin)
- **Cause**: Running `sddm-greeter-qt6 --test-mode` creates a full-screen window on your active display. On Wayland compositors (such as KWin on KDE Plasma 6), override-redirect or X11 bypass windows (`Qt.X11BypassWindowManagerHint`) can be hidden beneath the preview window, leaving no exit button visible.
- **Resolution**:
  - **Floating Exit Overlay**: A dedicated floating pill appears at the top-center of the screen labeled `✕ Stop Live Greeter Preview`. Click it to close the preview immediately.
  - **App Window Banner**: If you switch back to SDDM Theme Manager (`Alt+Tab`), a prominent red top banner with `[ ✕ Stop Live Preview ]` is always available.
  - **Keyboard Shortcuts**:
    - Press `Esc` while SDDM Theme Manager is focused.
    - Press `Alt+F4` on the preview window (launched with `--qwindowtitle` support so window managers can close it).
  - **Terminal Emergency Kill**:
    ```bash
    killall sddm-greeter-qt6 || killall sddm-greeter
    ```

### 6. Theme Preview / Screenshot Missing or Showing Blank Card
- **Cause**: Many community SDDM themes do not package a standard `preview.png` in their root directory. They may place images in subdirectories (`screenshots/`, `images/`, `backgrounds/`, `assets/`, `wallpapers/`), use localized names (`elarun.jpg`, `hi_IN.png`), or use video backgrounds (`.mp4`, `.webm`).
- **Resolution**:
  - SDDM Theme Manager automatically scans all nested asset directories for valid preview images.
  - For themes using video backgrounds, it automatically invokes `ffmpeg` to extract a preview frame. Install `ffmpeg` if not present:
    ```bash
    sudo pacman -S ffmpeg   # Arch / CachyOS / Manjaro
    sudo dnf install ffmpeg # Fedora
    sudo apt install ffmpeg # Debian / Ubuntu
    ```
  - For themes lacking any graphical assets, the app automatically generates an informative visual fallback preview card with the theme title and Qt version, ensuring cards are never blank.

### 7. Duplicate Theme Cards or `⚠️ NEEDS SYNC` Status Badge
- **Cause**: When a theme exists in your user directory (`~/.local/share/sddm/themes/`) but has not yet been copied to `/usr/share/sddm/themes/`, SDDM will not be able to display it on boot. SDDM Theme Manager deduplicates duplicate folders by theme ID and displays a `⚠️ NEEDS SYNC` badge on incomplete themes.
- **Resolution**: Select the card and click **"Sync to SDDM"** in the details panel, or right-click the card and choose **"Sync to SDDM"**. You can also synchronize all user themes at once via the toolbar button **"Sync All User Themes"**.

### 8. Bypassing Polkit During Development
If you prefer not to configure Polkit rules or want to test features immediately, launch the application with `--no-polkit`:
```bash
python3 main.py --no-polkit
```
This forces all privileged file operations to use standard `sudo` instead of `pkexec`.

---

## 🛠️ Command Line Usage & Flags

```bash
sddm-theme-manager [OPTIONS]
```

### Options:
- `--apply-scheduled`:
  Headless automation flag: checks current time against Day/Night scheduler configuration (`~/.config/sddm-theme-manager/scheduler.json`) and applies the appropriate theme.
  *Used by systemd user timers.*
  ```bash
  sddm-theme-manager --apply-scheduled
  ```
- `--no-polkit`:
  Development & testing fallback that bypasses `pkexec` and calls elevated commands with `sudo` instead.
  *Prints a warning on startup.*
  ```bash
  python3 main.py --no-polkit
  ```
- `--debug`:
  Prints detailed logs of all subprocess commands, arguments, exit codes, and output streams:
  ```bash
  python3 main.py --debug
  ```
- `--version`:
  Displays the application version.

---

## 🔨 Packaging with PyInstaller

To bundle the application into a single standalone binary:

```bash
cd ~/sddm-theme-manager
./build.sh
```

Or run PyInstaller directly via `uvx`:
```bash
uvx pyinstaller \
    --name sddm-theme-manager \
    --onefile \
    --windowed \
    --add-data "ui/styles.qss:ui" \
    --add-data "resources:resources" \
    --icon "resources/icons/sddm-theme-manager.png" \
    main.py
```

The output binary will be generated at `dist/sddm-theme-manager`.

---

## 📁 SDDM Architecture & Theme Resolution

### 1. Configuration File Priority
SDDM reads its configuration files in the following priority order (highest priority wins):
1. `/etc/sddm.conf.d/*.conf` (drop-in configuration files, sorted lexicographically)
2. `/etc/sddm.conf` (legacy monolithic configuration)
3. `~/.config/sddm.conf` (user configuration)

When you apply a theme, **SDDM Theme Manager** writes to `/etc/sddm.conf.d/10-theme.conf` with:
```ini
[Theme]
Current = <theme-name>
```
Existing custom sections and keys are preserved without touching the system `/etc/sddm.conf`.

### 2. Daemon Security Model & Theme Storage
- **Theme Directory (`ThemeDir`)**: SDDM's built-in default theme directory is `/usr/share/sddm/themes/`.
- **User Isolation**: The SDDM display manager runs as a dedicated system user (`sddm`, UID 952). Because user home directories (`/home/<user>/`) have restrictive `700` (`drwx------`) permissions on modern Linux systems, user `sddm` cannot traverse or read files stored under `~/.local/share/sddm/themes/`.
- **Automated Synchronization**: To ensure themes work seamlessly without compromising your home directory security, SDDM Theme Manager automatically normalizes permissions (`0755` directories, `0644` files) and synchronizes user themes to `/usr/share/sddm/themes/` whenever they are downloaded, installed, or applied.

---

## 📋 Changelog & Recent Updates

### v1.1.0
- **Transformation into Complete SDDM Control Center with 10 New Features**:
  1. **Desktop Wallpaper Synchronization**: 1-click sync from active desktop environment (KDE Plasma, Hyprland, GNOME, Sway, Feh, Nitrogen, XFCE) directly to SDDM background.
  2. **Dynamic Palette & Pywal Accent Color Extraction**: Samples dominant and accent colors via native Qt `QImage` pixel analysis, and reads Pywal cache (`~/.cache/wal/colors.json`).
  3. **Animated & Video Wallpapers**: Full support for `.mp4`, `.webm`, `.mkv`, and `.gif` animated backgrounds with poster thumbnail extraction.
  4. **Visual Theme Customizer (Theme Tweaker)**: Interactive GUI dialog to customize clock format (12h/24h), login box alignment, blur radius slider, dimming opacity slider, font picker, and base size.
  5. **User Profile Avatar Manager**: Circular crop tool and manager for user login icons in both `~/.face.icon` and AccountsService (`/var/lib/AccountsService/icons/<user>`).
  6. **Day / Night Automated Theme Scheduler**: Scheduled transitions between light and dark themes backed by a lightweight systemd user timer (`sddm-theme-scheduler.timer`) and `--apply-scheduled` CLI mode.
  7. **Qt5 vs Qt6 Compatibility Linter & Auto-Patcher**: Scans QML files for deprecated modules (`QtGraphicalEffects`) and offers 1-click auto-patching to `Qt5Compat.GraphicalEffects 6.0` with safety `.bak` backups.
  8. **Multi-Monitor Display Manager**: GUI to select primary SDDM display across connected outputs and configure `/usr/share/sddm/scripts/Xsetup`.
  9. **SDDM Daemon & Autologin Control Panel**: Manage autologin user, session choice (scans Wayland & X11 sessions), and boot NumLock state in `/etc/sddm.conf.d/`.
  10. **1-Click Theme Backup, Exporter & Sharing**: Packages custom themes, wallpapers, and overrides into shareable `.tar.gz` / `.tar.zst` bundles with `manifest.json`.
- **Direct-to-System Storage Architecture**:
  - All downloads and archive installations now extract directly into `/usr/share/sddm/themes/` with permissions pre-normalized, eliminating duplicate entries.
  - 1-click theme removal completely wipes `/usr/share/sddm/themes/` and purges any legacy user copy simultaneously.
- **Real-Time Filesystem Live Tracking**:
  - Integrated `QFileSystemWatcher` to track `/usr/share/sddm/themes`, user directory, and `/etc/sddm.conf.d/`. External changes update the UI automatically without manual refresh.
- **Automated Test Suite Expansion**:
  - Expanded test suite from 126 to **195 automated unit and integration tests**, achieving 100% pass rate.

### v1.0.2
- **Universal Pipeline for Future Theme Downloads**:
  - Every theme downloaded from the KDE Store or installed from a `.tar.gz`/`.zip` file is now automatically provisioned with **both** system privileges and visual previews.
  - **Auto-Sync to System**: Downloaded themes are automatically synced to `/usr/share/sddm/themes/` with world-readable permissions (`0755` dirs, `0644` files) so SDDM can load them immediately on boot.
  - **Guaranteed Previews**: High-resolution screenshots are downloaded directly from the store (`previewpic1`). If a theme has no screenshots, it automatically extracts video frames via `ffmpeg` or renders a clean 800×450 `preview.png` on disk.
  - **Clean Uninstallation**: When removing a user theme, any corresponding synced copy in `/usr/share/sddm/themes/` is automatically cleaned up.
- **Automated SDDM System Theme Synchronization**:
  - SDDM daemon only reads themes from `/usr/share/sddm/themes/`. Newly installed user themes (`~/.local/share/sddm/themes/`) are now automatically verified, normalized with `a+rX` permissions, and synchronized to `/usr/share/sddm/themes/` whenever applied.
  - Added dedicated **"Sync to SDDM"** buttons in the toolbar and details panel, plus **"Sync All User Themes"** for bulk synchronization.
  - Added real-time **System Theme Health Checker** that warns if a configured theme is missing from `/usr/share/sddm/themes/` and offers a 1-click **"⚡ Fix & Sync to SDDM Now"** repair button.
  - Prevented Apply button lockouts: Active themes can now be re-applied or re-synced at any time.
- **Wayland-Compatible Live Preview & Exit Overlay**:
  - Removed X11-only bypass window manager flags that prevented the exit overlay from appearing on Wayland/KWin compositors.
  - Positioned floating top-center exit pill with periodic re-raising to stay above full-screen SDDM test windows.
  - Added prominent **Top Warning Banner** in main window with instant `[ ✕ Stop Live Preview ]` button and global `Esc` key handling.
  - Added `--qwindowtitle` to greeter subprocess so window managers allow standard `Alt+F4` close events.
- **Deep Preview Image Discovery & Video Background Extraction**:
  - Expanded thumbnail scanner to detect images across `preview.*`, `screenshot.*`, `screenshots/`, `images/`, `backgrounds/`, `assets/`, and `wallpapers/`.
  - Added automatic video background frame extraction via `ffmpeg` for themes with `.mp4` or animated backgrounds.
- **Polkit Permissions & Non-Blocking Execution**:
  - Added `/usr/bin/chmod` to `40-sddm-theme-manager.rules`.
  - Pre-normalized user file permissions before elevated copying to avoid permission hangs.

### v1.0.1
- **Polkit Engine Fix**:
  - Replaced `action.lookup("argv")` with `action.lookup("command_line")` in `40-sddm-theme-manager.rules` to prevent `TypeError: cannot read property 'length' of undefined` in `polkitd` on Arch Linux.
  - Added support for both `systemctl restart sddm` via D-Bus and `pkexec systemctl restart sddm`.
- **In-App Error Guidance**:
  - Updated the "Failed to Apply Theme" error dialog with actionable copy-paste troubleshooting steps if Polkit authorization fails.
- **INI Case-Preservation**:
  - Added `parser.optionxform = str` across `theme_applier.py`, `background.py`, and `theme_scanner.py` to ensure SDDM keys (`Current=...`, `background=...`) preserve exact case.
- **Desktop Entry Warning Fix**:
  - Fixed `setDesktopFileName` in `main.py` by removing redundant `.desktop` suffix.
- **Thread Safety**:
  - Added graceful thread shutdown in `StoreDialog` to prevent `QThread: Destroyed while thread is still running` exceptions.
- **Comprehensive Test Suite**:
  - Added 126 automated sandbox unit tests validating all core operations, UI initialization, theme installation, and background management.

---

## 📂 Project Structure

```
~/sddm-theme-manager/
├── main.py                          # Entry point & CLI argument parser
├── core/
│   ├── theme_scanner.py             # Discovers themes & detects active theme
│   ├── theme_applier.py             # Writes drop-in config & restarts SDDM
│   ├── background.py                # Manages theme.conf.user overrides
│   ├── installer.py                 # Direct /usr/share/sddm installer & 1-click cleaner
│   ├── preview.py                   # Manages sddm-greeter --test-mode subprocess
│   ├── polkit.py                    # Elevated pkexec / sudo runner
│   ├── store_client.py              # KDE Store / Pling OCS API client
│   ├── desktop_wallpaper.py         # Multi-DE active wallpaper detector & synchronizer
│   ├── color_palette.py             # Dominant palette & Pywal color extractor
│   ├── video_background.py          # Animated & video wallpaper manager (MP4/WebM/GIF)
│   ├── theme_configurator.py        # Visual theme tweaker engine (clock, blur, dim, font)
│   ├── avatar_manager.py            # User profile login picture manager
│   ├── scheduler.py                 # Automated Day/Night theme switcher & systemd timer
│   ├── linter.py                    # Qt5 vs Qt6 compatibility scanner & auto-patcher
│   ├── exporter.py                  # Portable theme bundle packager (.tar.gz/.tar.zst)
│   ├── display_manager.py           # Multi-monitor display detector & Xsetup configurator
│   └── daemon_config.py             # SDDM daemon settings, autologin, & session manager
├── ui/
│   ├── main_window.py               # Main window, toolbar, status bar & live watcher
│   ├── theme_grid.py                # Scrollable card grid with filter & sort
│   ├── detail_panel.py              # Metadata panel & quick action tool buttons
│   ├── store_dialog.py              # KDE Store browser modal
│   ├── tweaker_dialog.py            # Interactive visual theme customizer dialog
│   ├── avatar_dialog.py             # Circular profile avatar cropping dialog
│   ├── scheduler_dialog.py          # Day/Night automated schedule dialog
│   ├── linter_dialog.py             # Theme compatibility report & auto-patcher modal
│   ├── display_dialog.py            # Primary monitor selection dialog
│   ├── daemon_dialog.py             # SDDM daemon autologin & session settings dialog
│   ├── preview_overlay.py           # Floating exit pill during live greeter preview
│   └── styles.qss                   # Modern DE-agnostic dark/light stylesheet
├── polkit/
│   └── 40-sddm-theme-manager.rules   # JavaScript Polkit rule file
├── resources/
│   ├── icons/
│   │   ├── sddm-theme-manager.svg
│   │   └── sddm-theme-manager.png
│   └── sddm-theme-manager.desktop   # Application launcher entry
├── pyproject.toml                   # Build & dependency metadata
├── build.sh                         # PyInstaller standalone build script
├── install.sh                       # Installer for system/user/polkit
├── uninstall.sh                     # Uninstallation script for clean removal
└── README.md                        # Documentation
```

---

## ⚖️ License

MIT License. Designed and crafted for Linux desktop users across all environments.
