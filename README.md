# SDDM Theme Manager

A standalone, desktop-environment-agnostic GUI application for managing, customizing, and ricing [SDDM](https://github.com/sddm/sddm) (Simple Desktop Display Manager) Qt 5 & Qt 6 themes.

> [!NOTE]
> **Built for GNOME, Hyprland & Independent Window Managers**:
> While KDE Plasma includes a built-in SDDM configuration module in its System Settings, users of **GNOME**, **Hyprland**, **Sway**, **River**, **Wayfire**, **bspwm**, and **i3** have lacked a dedicated graphical control center to preview, edit, configure, and rice SDDM greeters.
> **SDDM Theme Manager fills this gap**, providing a complete, independent, first-class suite with Wayland compositor support (`hyprpaper`, `swww`, `swaybg`, `feh`), live greeter testing with non-trapping exit overlays, automated Polkit privileges, and 20 Next-Gen ricing features.

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

- **📁 "Install from File" Dual-Card Chooser & Theme Scaffolding**:
  - **Dual-Card Chooser**: Interactive modal offering **"📁 Create Your Own"** and **"📦 Install from Archive"**.
  - **Inline Name Validation**: Real-time regex verification (`^[a-z0-9][a-z0-9-]{0,48}[a-z0-9]$`), length boundaries (2–50 chars), and directory collision detection against `/usr/share/sddm/themes/` and `~/.local/share/sddm/themes/`.
  - **Zero-Error Qt 6 Greeter Engine**: Reverse-engineered from production SDDM themes to eliminate greeter crashes (`Main.qml: No such file or directory` and `SddmComponents 2.0` property collisions).
  - **Complete Out-of-the-Box Scaffolding**: Automatically provisions a fully functioning Qt 6 / `SddmComponents 2.0` responsive `Main.qml` (user switching with avatar mask, session selector, 12h/24h clock, power buttons), `metadata.desktop` (`Type=sddm-theme`, `QtVersion=6`), `theme.conf`, `metadata.json`, and aesthetic 1920×1080 gradient `background.png` and `preview.png`.
  - **Auto-Healing Linter & Preview Safeguard**: Pre-validates `MainScript` existence before running greeter previews, and auto-scaffolds `Main.qml` for any broken or incomplete themes.

- **🛠️ Multi-File Theme Editor & Code Customizer**:
  - **Universal Access for All Themes**: 1-click **"✏️ Edit Theme…"** option available for both newly created and existing themes via the **Main Toolbar**, **Detail Panel**, and **Card Right-Click Context Menu**.
  - **Multi-File Navigation & Discovery**: Dropdown file selector (`QComboBox`) automatically indexes and allows switching between all files in any theme:
    - `theme.conf` (Main SDDM Greeter configuration)
    - `theme.conf.user` (User overrides)
    - `metadata.desktop` (SDDM desktop environment metadata)
    - `metadata.json` (Theme package properties)
    - `Main.qml`, `login.qml`, and nested QML components (`Components/*.qml`)
    - Any auxiliary script or stylesheet files
  - **Dual Highlighters**:
    - `INISyntaxHighlighter`: Catppuccin Mocha syntax colors for sections, keys, `=`, values, `# comments`, and underlined missing values.
    - `QMLSyntaxHighlighter`: Highlighting for QML components, keywords, properties, numbers, strings, and multi-line comments (`/* ... */`).
  - **Live INI Validation & Escape Badges**: Monospace line numbering gutter with real-time detection of unrecognized escape sequences (⚠️ badges).
  - **Debounced Live Preview (300ms)**: Real-time background parser with escape resolution (`\n`, `\t`, `\s`, `\\`), dynamic aspect-ratio scaling, video/color badges, and metadata info strip (`resolution`, `file size`).
  - **⚡ Live Dev & Diagnostic Studio (1+2+3+4 Architecture)**:
    - **`▶ Live Test (F5)` & `⏹ Stop (Shift+F5)`**: Directly launches live greeter test mode (`sddm-greeter-qt6` or `sddm-greeter`) asynchronously with process supervision and PID monitoring.
    - **Real-Time Diagnostic Console Drawer**: Collapsible dark terminal that streams stdout/stderr in real time, colorizing errors (🔴), warnings (🟡), and info (🟢).
    - **1-Click Error Navigation**: Regex parses runtime QML errors (`Main.qml:42`) and provides clickable links that immediately switch the editor file and jump to the exact offending line.
    - **Actionable Suggestions Engine**: Inlines intelligent fix recommendations for common SDDM errors (e.g. `Library import requires a version`, `Button.background` property conflicts, missing Qt modules).
    - **Pre-Flight Static Validation**: Instantly verifies brace balance and entrypoint files before spawning the greeter to prevent unhandled parse crashes.
    - **Hot-Reload on Save (`Ctrl+S`)**: Automatically re-runs the live greeter on save for rapid visual feedback.
  - **Integrated File Creator**: Built-in **"➕ New File…"** tool to scaffold new files (`theme.conf.user`, QML components) directly inside the theme directory.
  - **Polkit-Aware Save & Apply**: Dedicated buttons for **"💾 Save File"** (`Ctrl+S`) and **"⚡ Save & Apply"** (saves file, updates `/etc/sddm.conf.d/10-theme.conf`, restarts SDDM, and presents a 2-second restarting overlay).

- **📦 Enhanced Archive Installation & Conflict Backup**:
  - **Single-Wrapped-Folder Flattening**: Detects nested theme subdirectories and automatically flattens them to the theme root.
  - **Strict Syntax Verification**: Verifies `theme.conf` existence and parses INI syntax with exact line number reporting on error.
  - **Conflict Resolution & Backups**: Prompts for confirmation when replacing an existing theme and automatically backs up the existing version to `<name>.bak.<timestamp>/`.
  - **Non-Blocking Large Archive Extraction**: Leverages `QThreadPool` and `QRunnable` for archives exceeding 10 MB to prevent UI freezes.

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

## 📦 Installation & Automated Self-Healing Setup

The included `install.sh` script is an **automated, self-healing installer** that sets up the application and automatically resolves common Linux permissions, Polkit configurations, and desktop launcher pitfalls.

### User-Level Installation (Recommended)
```bash
cd ~/sddm-theme-manager
./install.sh
```
Installs the application into `~/.local/` and automatically:
- Checks system dependencies (`Python 3`, `PyQt6`, `SDDM`, `greeters`, `ffmpeg`).
- Generates desktop launcher with **absolute executable paths** (eliminating menu launch failures).
- Refreshes desktop application menus, GTK icon caches, and KDE Sycoca databases immediately.
- Idempotently adds `~/.local/bin` to your `~/.bashrc` and `~/.zshrc` if not present in `$PATH`.
- Prompts to install Polkit rules (`root:root 644`) for passwordless theme management.
- Normalizes SDDM system directories (`/usr/share/sddm/themes` with `0755` permissions) and syncs user themes.

### System-Wide Installation
```bash
cd ~/sddm-theme-manager
sudo ./install.sh --system
```
Installs system-wide to `/usr/local/bin` and `/usr/local/share/sddm-theme-manager`.

### ⚡ Automated 1-Click Repair Mode
If you ever encounter permission errors, missing Polkit rules, or themes not showing up in SDDM on boot, run:
```bash
./install.sh --repair
```
*(Or `sudo ./install.sh --repair`).*
This diagnoses and automatically repairs Polkit rules, SDDM directory permissions, user theme sync, and desktop launcher caches in one step.

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

## ⚠️ Troubleshooting & Automated Self-Healing

> [!TIP]
> ### ⚡ Automated 1-Click Fix via `install.sh --repair`
> Instead of manually diagnosing and copy-pasting individual commands below, run the built-in repair suite:
> ```bash
> cd ~/sddm-theme-manager
> ./install.sh --repair
> ```
> *(Or `sudo ./install.sh --repair`).*
> This script automatically detects and resolves:
> - Polkit rules missing, misconfigured, or having wrong ownership/permissions (auto-sets `root:root 644`).
> - Restarts and verifies the Polkit system service via systemd journal logs.
> - SDDM system directories (`/usr/share/sddm/themes`, `/etc/sddm.conf.d`) permissions and auto-syncs user themes so SDDM never reverts to Breeze.
> - Refreshes desktop launcher shortcuts, icons, and KDE Sycoca application databases.
> - Verifies shell `$PATH` and configures `~/.local/bin` in `~/.bashrc` and `~/.zshrc`.
> - Validates Python, PyQt6, SDDM greeters, and ffmpeg dependencies.

---

### Manual Resolutions & Technical Explanations

### 1. `Failed to write configuration: Error executing command as another user: Not authorized`
- **Cause**: Either the Polkit rule is not installed in `/etc/polkit-1/rules.d/`, or an older rule using `action.lookup("argv")` caused a JavaScript `TypeError` in `polkitd` because Polkit provides `action.lookup("command_line")` instead of an array.
- **Resolution (Automated)**: Run `./install.sh --repair`
- **Resolution (Manual)**: Copy the updated rule file and restart Polkit:
  ```bash
  sudo cp ~/sddm-theme-manager/polkit/40-sddm-theme-manager.rules /etc/polkit-1/rules.d/
  sudo chown root:root /etc/polkit-1/rules.d/40-sddm-theme-manager.rules
  sudo chmod 644 /etc/polkit-1/rules.d/40-sddm-theme-manager.rules
  sudo systemctl restart polkit
  ```

### 2. `cp: cannot stat '/root/sddm-theme-manager/...': No such file or directory`
- **Cause**: If you switched to a root shell (`sudo su`), `~` resolves to `/root/` instead of your user's home directory (`/home/<user>/`).
- **Resolution (Automated)**: Run `./install.sh --repair` (the script automatically resolves `$SUDO_USER` and the real home directory).
- **Resolution (Manual)**: Use the explicit path from your user directory:
  ```bash
  cp /home/$USER/sddm-theme-manager/polkit/40-sddm-theme-manager.rules /etc/polkit-1/rules.d/
  chown root:root /etc/polkit-1/rules.d/40-sddm-theme-manager.rules
  chmod 644 /etc/polkit-1/rules.d/40-sddm-theme-manager.rules
  systemctl restart polkit
  ```

### 3. `Permission denied` when copying to `/etc/polkit-1/rules.d/`
- **Cause**: The `/etc/polkit-1/rules.d/` directory has strict `700` (`rwx------`) permissions owned by `root`. Standard user shells cannot view or write files there without privilege elevation.
- **Resolution (Automated)**: Run `./install.sh --repair` (prompts for elevation automatically).
- **Resolution (Manual)**: Always prefix copy, chown, and chmod commands with `sudo`:
  ```bash
  sudo cp ~/sddm-theme-manager/polkit/40-sddm-theme-manager.rules /etc/polkit-1/rules.d/
  sudo chown root:root /etc/polkit-1/rules.d/40-sddm-theme-manager.rules
  sudo chmod 644 /etc/polkit-1/rules.d/40-sddm-theme-manager.rules
  sudo systemctl restart polkit
  ```

### 4. `Launching SDDM Theme Manager (Failed): Could not find the program 'sddm-theme-manager'`
- **Cause**: On Linux desktop environments (such as KDE Plasma or GNOME), desktop shortcuts with relative command paths (`Exec=sddm-theme-manager`) rely on the desktop session's `$PATH`. User binary directories like `~/.local/bin` are frequently not in the desktop session's `$PATH` by default.
- **Resolution (Automated)**:
  Run `./install.sh --repair` which writes the exact absolute executable path (e.g. `Exec=/home/<user>/.local/bin/sddm-theme-manager`), updates desktop databases, and adds `~/.local/bin` to your `~/.bashrc` / `~/.zshrc`.
- **Resolution (Manual)**:
  ```bash
  update-desktop-database ~/.local/share/applications/
  kbuildsycoca6 --noincremental   # For KDE Plasma
  ```

### 5. Applied Theme Does Not Show in SDDM (Reverts to Default Breeze)
- **Cause**: SDDM runs as a dedicated system user (`sddm`, UID 952). The SDDM daemon reads `Current=<theme-name>` from `/etc/sddm.conf.d/10-theme.conf` and searches for the theme in `/usr/share/sddm/themes/`. If a theme only exists in user storage (`~/.local/share/sddm/themes/`), SDDM cannot access it because Linux user home directories usually have mode `700` (`drwx------`). When SDDM fails to locate or read the theme directory, it silently falls back to the default `breeze` theme.
- **Resolution (Automated)**:
  - Run `./install.sh --repair` to automatically copy un-synced user themes to `/usr/share/sddm/themes/` with normalized `0755` directory and `0644` file permissions.
  - Or click the **"⚡ Fix & Sync to SDDM Now"** button in the health alert banner inside the app.
- **Resolution (Manual)**:
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

### v1.5.0 — UI De-Collision, Live Business Logic Daemon & GNOME / Hyprland Ricing Hub
- **🖥️ Dedicated for GNOME, Hyprland & Wayland Tiling Compositors**:
  - Purpose-built for users who lack KDE Plasma's System Settings KCM module, bringing full GUI management, live previews, and automated privileges to GNOME, Hyprland, Sway, and independent window managers.
  - Native integration with Hyprland (`swww`, `hyprpaper`) and GNOME GSettings for 1-click desktop wallpaper matching.
  - Wayland greeter preview window management with non-trapping floating exit pill and instant `Esc` emergency kill.
- **✨ Complete Greeter UI Layout De-Collision & Status Docks**:
  - Solved all widget collisions and overlapping elements in equipped greeters.
  - **`nextgenTopBar` (Top-Center, `z: 30`)**: Centered status island grouping the **Media Capsule**, **FIDO2 Hardware Key Indicator**, and **System Hardware HUD**.
  - **`nextgenActionDock` (Top-Right, `z: 40`)**: Floating pill dock grouping compact interactive pills for **Mobile Passkey QR**, **Sticky Notes**, and **🎮 Mini-Games**.
  - The bottom region of the display is kept 100% clear for SDDM default components (user card, password field, session switcher, reboot/shutdown buttons).
- **⚙️ Live Telemetry & Command Daemon (`core/live_daemon.py`)**:
  - Lightweight background daemon running at ~1 Hz synchronizing real-time MPRIS player metadata, hardware metrics (CPU temp, RAM used/total, free root disk, battery charging status, pending updates), USB sysfs FIDO2 key presence, and household sticky notes.
  - Writes world-readable status files to `/tmp/sddm-*.json` accessible by greeter sessions.
- **🌐 Embedded Passkey & Feature HTTP REST API (`core/passkey_server.py`)**:
  - Embedded local HTTP daemon listening on `http://127.0.0.1:8089/` serving:
    - `/api/telemetry` — Live hardware sensor metrics.
    - `/api/mpris` & `/api/mpris/{play-pause|next|previous}` — Live media metadata and remote playback control.
    - `/api/fido` — USB security key presence & state.
    - `/api/notes` — Pre-login memo bulletin notes.
    - `/auth/<id>/status` & `/auth/<id>/verify` — Mobile biometric authorization.
- **🔒 Qt 6 Local File XHR Security Resolution**:
  - Injected `QML_XHR_ALLOW_FILE_READ=1` into preview and live greeter environments, resolving Qt 6's default security block on local `file:///` `XMLHttpRequest` calls.
- **🎵 Interactive Media Playback Controls**:
  - Greeter Media Capsule island now features interactive `MouseArea` controls (⏮ ⏯ ⏭) with command queues executing real `playerctl` and D-Bus actions.
- **🌟 Next-Gen Suite Hub & Dedicated Desktop Dialogs**:
  - Added **"🌟 Next-Gen Suite ▾"** toolbar dropdown in `MainWindow` with 1-click access to all 20 features:
    - **[StickyNotesDialog](ui/sticky_notes_dialog.py)** (Feature 12): Add, edit, remove, and sync pre-login household memos.
    - **[ChameleonDialog](ui/chameleon_dialog.py)** (Feature 18): 1-click generator for macOS Sequoia, Windows 11, ChromeOS, and Cyberpunk HUD presets.
    - **[AIRicingDialog](ui/ai_ricing_dialog.py)** (Feature 16): Natural language prompt-to-theme synthesizer.
    - **[SecurityDialog](ui/security_dialog.py)** (Features 6, 7, 8, 9): Passkey QR preview, FIDO2 rescan, duress panic PIN, and BLE proximity.
    - **[MarketplaceDialog](ui/marketplace_dialog.py)** (Feature 19): Decentralized community theme catalog and `.tar.gz` publisher.
    - **[MonetizationDialog](ui/monetization_dialog.py)** (Feature 20): Artist tipping links and Supporter Pro Pass management.
- **📜 DetailPanel Scroll Overflow Fix**:
  - Moved the actions box inside `self.content_layout` within `self.scroll_content`, eliminating button clipping on compact screen resolutions.
- **🧪 Comprehensive Test Suite Milestone**:
  - Expanded test suite to **610 automated unit and integration tests across 45 test sections** with **100% pass rate (0 failures)**.

### v1.4.0 — Universal Theme Enhancer & Next-Gen Master Suite Template
- **⚡ Universal Theme Enhancer Engine (`core/theme_enhancer.py`)**:
  - **Universal 1-Click Upgrade for Existing Themes**: Easily equips *any* existing installed SDDM theme (`star-rail`, `nier-automata`, `Slot-Silvery-SDDM-6`, `pixel-hollowknight`, etc.) with the complete Next-Gen sensory, visual, and telemetry suite.
  - **Full Suite Integration**: Automatically generates and wires 8 modern companion QML widgets (`ShaderBackground.qml`, `WeatherCanvas.qml`, `MediaCapsule.qml`, `SystemHUD.qml`, `StickyNotesWidget.qml`, `PasskeyWidget.qml`, `Fido2Visualizer.qml`, `GameFlappytux.qml`) and enables non-blocking SDDM boot chime audio playback in `/usr/share/sddm/scripts/Xsetup`.
  - **Non-Destructive Fail-Safe Architecture**: Automated backup (`Main.qml.pre_enhance_bak`) created before injecting anchors, ensuring zero risk of theme corruption or data loss.
  - **1-Click Clean Rollback**: Instant clean restoration from backup, safely restoring original files and purging injected companion QMLs.
  - **Interactive Dialog (`ui/theme_enhancer_dialog.py`)**:
    - Real-time feature inspection badges detecting active and inactive features.
    - Sound preset selector (*Macintosh Platinum*, *PS2 Ambient*, *Win98 Wave*, *Cyber Beep*, *Mechanical Click*) with live **"▶ Test"** audio preview.
    - Procedural GLSL shader selector (*Matrix Digital Rain*, *Retro Synthwave Grid*, *Neon Waves*, *Fluid Nebula*, *Deep Space Starfield*).
    - 1-Click batch upgrade button and 1-Click rollback button.
  - **Universal UI Entry Points**:
    - **Main Toolbar**: Prominent **"⚡ Equip…"** button.
    - **Detail Panel**: Dedicated **"⚡ Equip Next-Gen Features…"** action button.
    - **Grid Context Menu**: Right-click any theme card → **"⚡ Equip Next-Gen Features…"**.
- **🌟 Next-Gen Master Suite Template (`mode="nextgen"`)**:
  - New 5th creation mode in **"Install from File" → "📁 Create Your Own"** wizard (`InstallDialog`) and `ThemeWriter.scaffold_theme(mode="nextgen")`.
  - Automatically scaffolds 14 files and assets: comprehensive Qt 5 & Qt 6 dual-compatible `Main.qml`, 8 companion widgets, `metadata.desktop`, `theme.conf`, 1080p `background.png`, and `preview.png`.
  - Includes responsive glass cards, user switching, avatar mask, session selector, dynamic island MPRIS controls, weather/lunar particle canvas, cold boot HUD hardware telemetry, mobile passkey QR, and mini-game easter egg (`Ctrl+Alt+G`).
  - Interactive **Theme Tutorial Dialog** updated with an exact 60-word technical specification for Next-Gen Master Mode.
- **Automated Test Suite Expansion**:
  - Test suite expanded from 481 to **556 automated unit and integration tests across 44 sections** with a **100% pass rate (0 failures)**.

### v1.3.0 — The 20 Groundbreaking Features Next-Gen Suite
- **🛡️ Phase 0: Foundation & Safety Shield**:
  - **Feature 11: "Boot Shield" Never-Get-Locked-Out Watchdog (`core/boot_shield.py`)**:
    - Automated systemd watchdog service (`sddm-boot-shield.service`) and monitor daemon (`/usr/local/bin/sddm-boot-shield`).
    - Watches SDDM greeter stability; if a broken theme, corrupt shader, or segfault occurs, automatically reverts `/etc/sddm.conf.d/10-theme.conf` to safe default `breeze` (or first verified system theme) and restarts SDDM within 4 seconds.
    - CLI validation flag: `sddm-theme-manager --verify-shield`.
    - Main window status bar: Live **"🛡️ Shield: Active"** status badge and click-to-open **Safety Center Dialog** with crash logs and emergency rollback test.

- **🌌 Phase A: Sensory & Visual Immersion**:
  - **Feature 1: GLSL Fragment Shader Background Engine (`core/shader_engine.py`)**:
    - 5 built-in procedural GLSL fragment shaders: *Matrix Digital Rain*, *Retro Synthwave Grid*, *Pulsating Neon Waves*, *Cosmic Fluid Nebula*, and *Deep Space Starfield*.
    - Resolution-independent rendering (1080p to 8K) with zero video decoding overhead via QML `ShaderEffect`.
    - 1-click injection and clean restoration in any SDDM theme.
  - **Feature 2: SDDM Boot Chime & Audio Synthesizer (`core/audio_chime.py`)**:
    - Procedural audio synthesis producing standalone 16-bit PCM WAV chimes without external audio assets.
    - Sound presets: *PlayStation 2 Ambient*, *Macintosh Platinum*, *Windows 98 Ambient Wave*, *Cybernetic Voice Beep*, and *Mechanical Switch Click*.
    - Non-blocking startup hook in `/usr/share/sddm/scripts/Xsetup` with PipeWire (`pw-play`), PulseAudio (`paplay`), and ALSA (`aplay`) support.
  - **Feature 3: Real-Time Weather & Astronomical Cosmos (`core/weather_service.py`)**:
    - Queries Open-Meteo REST API (no API key required) for live temperature, conditions, and precipitation.
    - High-precision Julian astronomical calculator computing live moon phases (New Moon to Full Moon) and illumination.
    - Generates dynamic QML particle canvas rendering glass raindrops with refraction, falling snowflakes, or twinkling celestial stars.
  - **Feature 4: Pre-Login MPRIS Media Capsule (`core/mpris_bridge.py`)**:
    - Discovers running media players (Spotify, Firefox, VLC, MPD) and extracts live track metadata.
    - Writes world-readable shared telemetry to `/tmp/sddm-mpris.json` for isolated greeter sessions.
    - Generates floating "Dynamic Island" capsule with album art, track/artist marquee, and playback controls (⏮ ⏯ ⏭).
  - **Feature 5: 24-Hour Solar Time-Lapse & Satellite Imagery (`core/solar_timelapse.py`)**:
    - Computes continuous 24-hour solar elevation angles (Dawn, Golden Hour, Zenith High Noon, Sunset, Dusk, Midnight).
    - Maps wallpapers across 24 solar phases and provides live NOAA GOES geostationary Earth satellite frames.

- **🔐 Phase B: Security & Authentication Suite**:
  - **Feature 6: Cryptographic QR Passkey Mobile Login (`core/passkey_server.py`)**:
    - Local cryptographic challenge server creating time-limited HMAC-SHA256 session tokens.
    - Generates standalone SVG QR code matrix for passwordless biometric authentication from mobile devices.
  - **Feature 7: Bluetooth BLE Proximity Auto-Unlock (`core/ble_proximity.py`)**:
    - Bluetooth Low Energy RSSI scanner measuring signal strength from paired smartwatches and smartphones.
    - Log-distance path loss approximation calculating distance in meters and triggering auto-unlock within 1.2m.
  - **Feature 8: "Panic Mode" / Decoy Duress Profile (`core/panic_mode.py`)**:
    - Protects user privacy under duress by accepting a secondary decoy PIN.
    - Redirects login to an ephemeral guest sandbox with tmpfs overlay and zero access to private keys or documents.
    - Includes automated user permissions privacy audit for sensitive directories (`.ssh`, `.gnupg`, `.config`).
  - **Feature 9: FIDO2 / YubiKey Hardware Token Visualizer (`core/fido2_detector.py`)**:
    - Detects connected hardware security keys (YubiKey, Nitrokey, SoloKeys, Feitian) via USB/sysfs.
    - Generates holographic glowing key badge pulsing amber when awaiting touch and glowing green upon verification.

- **📊 Phase C: Power Tools & Telemetry**:
  - **Feature 10: "Cold Boot HUD" Pre-Login Hardware Telemetry (`core/system_hud.py`)**:
    - High-speed direct reader from `/proc` and `/sysfs` (CPU temp/load, RAM usage, battery health, root disk space, and pending package updates).
    - Generates sleek glass cyberpunk telemetry bar for SDDM greeters.
  - **Feature 12: Pre-Login Sticky Notes & Household Bulletin (`core/sticky_notes.py`)**:
    - Multi-user bulletin board storing pinned memo cards with expiration dates and colors.
    - Renders interactive floating sticky notes directly on the SDDM greeter.
  - **Feature 13: Multi-Session "Live Peek" Window (`core/session_peek.py`)**:
    - Integrates with `loginctl` to query active graphical sessions (Wayland/X11), desktop environments, and idle times.
    - Displays interactive user workspace preview switcher cards.
  - **Feature 18: "OS Chameleon" 1-Click Distro Hopper Presets (`core/chameleon_presets.py`)**:
    - 4 complete, pixel-perfect theme architectures: *macOS Sequoia Aerial*, *Windows 11 Fluent Acrylic*, *Steam Deck OLED Console*, and *Cyberpunk 2077 Netwatch HUD*.

- **🎨 Phase D: Developer & Creator Studios**:
  - **Feature 14: Zero-Code WYSIWYG Drag-and-Drop Theme Studio (`ui/studio_builder.py`)**:
    - Interactive visual Qt canvas with live property inspector, color pickers, border radius sliders, and layout presets (Center, Left, Split).
    - 1-click "Compile & Export" compiling designs directly into production-ready QtQuick QML packages.
  - **Feature 15: Hot-Reload "Live Studio" for Developers (`core/dev_reload.py`)**:
    - Dev simulation environment with mock hardware states: time-of-day slider, battery percentage and charging toggles, and multi-monitor aspect ratio switcher (16:9, 16:10, 21:9 Ultrawide, 9:16 Vertical).
  - **Feature 16: Prompt-to-Theme AI Ricing Engine (`core/ai_generator.py`)**:
    - Natural language prompt to theme generator interpreting aesthetic descriptions into harmonic palettes, typography, and complete QML themes.
  - **Feature 17: Interactive Pre-Login Mini-Games (`core/greeter_games.py`)**:
    - Pure-QML retro mini-games (*Flappy Tux*, *Cyber Pong 2077*) playable directly on the SDDM greeter screen.

- **🌐 Phase E: Ecosystem & Monetization**:
  - **Feature 19: Decentralized Theme Hub & "Rice-Drop" Marketplace (`core/marketplace.py`)**:
    - Git-backed community theme catalog with name search, tag filtering (minimal, cyberpunk, pastel, glass), star ratings, and 1-click `.tar.gz` bundle packaging.
  - **Feature 20: Built-in Creator Monetization ("Support the Rice") (`core/monetization.py`)**:
    - Discovers artist sponsorship metadata (`X-SDDM-Sponsor-Github`, `X-SDDM-Sponsor-Kofi`, `X-SDDM-Sponsor-Patreon`) and activates Supporter Pro Pass perks.

- **Test Suite Expansion**:
  - Test suite expanded from 358 to **481 automated unit and integration tests** with **100% pass rate (0 failures)**.

### v1.2.4
- **Live Dev & Diagnostic Studio (Unified 1+2+3+4 Architecture) in Theme Editor**:
  - **Layer 1: Live Play Greeter Runner (`LiveGreeterRunner`)**:
    - Direct **`▶ Live Test (F5)`** and **`⏹ Stop (Shift+F5)`** action controls in the editor header bar.
    - Spawns `sddm-greeter-qt6 --test-mode` (or `sddm-greeter` fallback) asynchronously via `QProcess` with live PID tracking and supervised process termination.
  - **Layer 2: Real-Time Diagnostic Console Drawer (`LiveConsoleDrawer`)**:
    - Collapsible dark diagnostic console docked beneath the editor streaming `stdout` and `stderr` in real time.
    - Color-coded log streams: 🔴 Errors, 🟡 Warnings, 🟢 Success/Info, 🔵 Pre-Flight.
    - **Clickable Error Jumps**: Parsing engine identifies `([a-zA-Z0-9_\-\.\/]+\.qml):(\d+)` and generates 1-click links (`👉 [⚡ Jump to Main.qml:42]`). Clicking automatically switches files and positions the cursor with immediate line highlighting.
    - **Actionable Quick-Fix Hints**: Automatically detects common SDDM greeter pitfalls (e.g., `Library import requires a version`, `Button.background` property conflicts, missing Qt modules, unhandled connection syntax) and presents an inline suggestion box.
  - **Layer 3: Instant Pre-Flight Static Validation**:
    - Sub-millisecond pre-flight checks before greeter spawn: verifies balanced `{}` `()` `[]` braces and ensures `MainScript` and entrypoint files exist.
    - Flags fatal syntax errors immediately in the console drawer without wasting CPU or crashing the display greeter.
  - **Layer 4: Hot-Reload Dev Mode (`[✓] Hot-Reload on Save`)**:
    - Toggle checkbox in the toolbar (`Hot-Reload`). When enabled, pressing **`Ctrl+S`** automatically saves the file, terminates the active greeter process, and relaunches the live test in under 0.5s for rapid visual iteration.
  - **Test Suite Expansion**:
    - Test suite expanded from 307 to **358 automated unit and integration tests** with 100% pass rate.

### v1.2.3
- **Automated Self-Healing Installer & Comprehensive Diagnostic Suite (`install.sh`)**:
  - **Automated Polkit Rule Provisioning & Hardening**:
    - Automatically installs `/etc/polkit-1/rules.d/40-sddm-theme-manager.rules` and `/usr/share/polkit-1/actions/com.sddmthememanager.policy` with strict, required `root:root 644` permissions.
    - Automatically restarts the `polkit` daemon via systemd and verifies journalctl logs to eliminate JavaScript TypeErrors or rule loading failures.
    - Accurately resolves real user (`$SUDO_USER`) and home paths to permanently prevent the `cp: cannot stat '/root/...'` path expansion pitfall.
  - **Absolute Desktop Paths & Seamless Application Menus**:
    - Generates desktop launcher shortcuts (`.desktop`) with exact absolute executable paths (`Exec=$BIN_DIR/$APP_NAME`), resolving the `Could not find the program 'sddm-theme-manager'` error across all desktop environments.
    - Automatically triggers `update-desktop-database`, `gtk-update-icon-cache`, and `kbuildsycoca6/5` to refresh KDE Plasma and GNOME app launchers immediately without rebooting.
  - **SDDM Permissions & User Theme Auto-Sync**:
    - Automatically normalizes `/usr/share/sddm/themes/` and `/etc/sddm.conf.d/` permissions (`0755` world-readable).
    - Automatically scans `~/.local/share/sddm/themes/` and synchronizes un-synced user themes to `/usr/share/sddm/themes/` with `0755` directory and `0644` file permissions so SDDM never reverts to Breeze on boot.
  - **Automated Shell PATH Integration**:
    - Detects whether `~/.local/bin` is in `$PATH` and provisions clean, idempotent exports into `~/.bashrc` and `~/.zshrc`.
    - Automatically creates `/usr/local/bin/sddm-theme-manager` universal symlink if `/usr/local/bin` is writable or when installing with privileges.
  - **Standalone 1-Click Repair Mode (`./install.sh --repair`)**:
    - Added `--repair` / `--fix` flag to run full self-healing diagnostics, repair permissions, sync user themes, fix Polkit rules, and refresh desktop databases in a single command.
  - **Environment & Dependency Diagnostics**:
    - Verifies Python 3 runtime, PyQt6 bindings, SDDM greeter binaries (`sddm-greeter-qt6` vs `sddm-greeter`), optional video thumbnail extractor (`ffmpeg`), and administrative group membership (`wheel`/`sudo`).

### v1.2.2
- **Smart Theme Scaffolder & Creation Template Modes (Combined 1+2+3+4 Architecture)**:
  - **100% Asset-Free Minimal Mode (Default)**: Completely eliminates unwanted dummy `background.png` and `preview.png` files during scaffolding. Creates only clean code and configs (`Main.qml`, `theme.conf`, `metadata.desktop`, `metadata.json`).
  - **Procedural Gradient Fallback in `Main.qml`**: Upgraded greeter template to render an aesthetic procedural dark gradient (`#16161e` → `#1f2335` → `#24283b`) with subtle ambient glow when `background=` is empty or missing, ensuring `sddm-greeter-qt6 --test-mode` executes with **zero errors and zero missing-image warnings**.
  - **Custom Wallpaper Direct Import**: In the "Create Your Own" form, selecting "Custom Wallpaper" provides an inline image picker to copy your actual wallpaper into the theme directory and automatically generate a matching `preview.png` thumbnail.
  - **Boilerplate Starter Option**: Preserved for beginners wanting a ready-to-test starter kit with synthetic 1080p background and preview assets.
  - **Granular Thumbnail Checkbox**: Independent `[ ] Generate preview.png thumbnail` toggle for fine-tuned control over directory contents.
- **Interactive Theme Files & Creation Modes Tutorial (`ThemeTutorialDialog`)**:
  - **Dual-Category Walkthrough**: Two interactive guide tabs covering:
    1. **Theme Files Guide (8 files)**: Exact 60-word specifications for `Main.qml`, `theme.conf`, `theme.conf.user`, `metadata.desktop`, `metadata.json`, `background.png`, `preview.png`, and `Components/`.
    2. **Template Modes Guide (4 modes)**: Exact 60-word specifications for `Minimal Code Mode`, `Custom Wallpaper Mode`, `Boilerplate Starter Mode`, and `Hybrid Asset Control`.
  - **Step-by-Step Navigation**: Smooth `[◀ Previous]` and `[Next ▶]` slide controls, `File X of 8` / `Mode X of 4` counters, sidebar jump list, syntax snippets, and 1-click `[✏️ Open in Editor]`.
  - **Universal Access**: Accessible via the Theme Editor's **"📖 Tutorial / Info"** menu (`F1`), the toolbar button, and the Install Dialog's **"📖 Mode Guide & Tutorial"** button.
- **Test Suite Expansion**: Test suite expanded from 282 to **307 automated unit and integration tests** with 100% pass rate.

### v1.2.1
- **Reverse-Engineered Complete SDDM Theme Scaffolding**:
  - **Zero-Error Greeter Entry Point**: Resolved `Main.qml: No such file or directory` SDDM greeter crash on newly created themes by reverse-engineering existing production themes (`star-rail`, `nier-automata`, `Slot-Silvery-SDDM-6`, `pixel-hollowknight`).
  - **Full Qt 6 & SddmComponents 2.0 Template**: `scaffold_theme()` now automatically generates a complete, responsive `Main.qml` supporting:
    - User switching with avatar masking (`OpacityMask`) and fallback icons.
    - Session switching across Wayland and X11 sessions (`sessionModel`).
    - Real-time 12h/24h digital clock and date header.
    - Password input with active focus, clear feedback, and SDDM greeter authentication signals (`onLoginFailed`, `onLoginSucceeded`).
    - Safe styled power action buttons (Reboot, Shut Down) avoiding `SddmComponents 2.0` Button property conflicts.
  - **Aesthetic Starter Wallpaper & Preview Generation**:
    - Automatically generates high-resolution 1920×1080 gradient `background.png` and 640×360 `preview.png` via native `QPainter` and `QLinearGradient`/`QRadialGradient`.
    - Automatically handles privileged copying into `/usr/share/sddm/themes/` using `write_binary_file()` and `copy_file_privileged()`.
  - **Complete Metadata Specifications**:
    - Generates `metadata.desktop` with required `Type=sddm-theme`, `QtVersion=6`, `MainScript=Main.qml`, and `ConfigFile=theme.conf`.
    - Generates `theme.conf` with visual defaults (`background=background.png`, `type=image`, `font=Sans`, `fontSize=11`, `color=#c0caf5`, `accentColor=#7aa2f7`, `clockFormat=24h`, `showClock=true`).
- **Live Greeter Preview Validation & Diagnostics**:
  - Enhanced `PreviewManager.start_preview()` to validate that the theme's `MainScript` exists prior to spawning `sddm-greeter-qt6`, preventing unhandled black screens and providing an actionable error notification.
- **Theme Linter & Auto-Patcher Missing Entry Detection**:
  - `ThemeLinter.lint_theme()` now verifies the existence of `Main.qml` and `MainScript` referenced in `metadata.desktop`.
  - `ThemeLinter.patch_theme_for_qt6()` automatically scaffolds a valid `Main.qml` if a theme directory is missing its entry script.
- **Test Suite Expansion**:
  - Test suite expanded to **259 automated unit and integration tests** with 100% pass rate, including automated `sddm-greeter-qt6 --test-mode` verification.

### v1.2.0
- **Multi-File Theme Viewing & Editing for All Themes**:
  - Added universal **"✏️ Edit Theme…"** action accessible for both existing and newly installed themes via the **Main Toolbar**, **Detail Panel**, and **Card Right-Click Context Menu**.
  - **Full File Tree Switcher**: Added an interactive `QComboBox` file selector in the Theme Editor to navigate, view, and edit any file in the theme directory: `theme.conf`, `theme.conf.user`, `metadata.desktop`, `metadata.json`, `Main.qml`, nested QML components (`Components/*.qml`), scripts, and text files.
  - **Dual Highlighting Engine**: Automatic switching between `INISyntaxHighlighter` (for `.conf`, `.ini`, `.desktop`, `.user`) and `QMLSyntaxHighlighter` (for `.qml`, `.js`, `.json`).
  - **In-Editor File Creator**: Built-in **"➕ New File…"** dialog to scaffold custom overrides (e.g. `theme.conf.user`, QML components) directly inside the theme directory.
  - **Dedicated Save Actions**: Added **"💾 Save File"** (`Ctrl+S`) for saving the active file and **"⚡ Save & Apply"** for saving and applying to the SDDM system greeter.
- **"Install from File" Dual-Card Modal Chooser**:
  - Replaced basic file dialog with an interactive dual-card chooser dialog offering **"📁 Create Your Own"** and **"📦 Install from Archive"**.
  - **Inline Name Validation**: Real-time regex verification (`^[a-z0-9][a-z0-9-]{0,48}[a-z0-9]$`), length boundaries (2–50 chars), and collision detection against system (`/usr/share/sddm/themes/`) and user directories.
  - **Automated Scaffolding**: Instantly provisions starter `theme.conf`, `metadata.json`, and `metadata.desktop` prior to launching the editor.
- **Dedicated INI & Code Theme Editor (`ThemeEditor`)**:
  - Separate 920×640 px dark dialog with dynamic dirty tracking (`Edit: <name> — <filename> *`).
  - **Syntax Highlighter (`INISyntaxHighlighter`)**: Catppuccin Mocha syntax highlighting for sections (`#89b4fa`), keys (`#a6e3a1`), operators (`#f9e2af`), values (`#cdd6f4`), comments (`#6c7086`), and underlined empty keys (`#f38ba8`).
  - **Line Number Gutter (`LineNumberArea`)**: Monospace line numbering with real-time escape sequence analyzer displaying ⚠️ warning badges for unrecognized escape sequences.
  - **Debounced Live Preview (300ms)**: High-speed preview renderer parsing `background=`, `type=`, and `font=` with escape resolution (`\n`, `\t`, `\s`, `\\`), dynamic aspect ratio scaling, video/color badges, and metadata info strip (`resolution`, `file size`).
  - **Polkit-Aware Save & Apply**: Directly updates `theme.conf`, updates `/etc/sddm.conf.d/10-theme.conf`, restarts SDDM via elevated polkit runner, and shows a 2-second restarting overlay.
  - **Keyboard Ergonomics**: Full shortcut bindings for `Ctrl+S` (Save File), `Ctrl+B` (Choose Background), `Ctrl+/` (Comment Toggle), `Tab` (4 Spaces), and `Esc` (Safe Exit Confirmation).
- **Hardened Archive Installation & Conflict Backup (`ArchiveInstaller`)**:
  - Added single-wrapped-folder detection and automatic extraction directory flattening.
  - Added strict `theme.conf` validation with syntax error reporting including exact line numbers.
  - Added conflict resolution prompting with automatic backup to `<name>.bak.<timestamp>/`.
  - Added non-blocking `QThreadPool` / `QRunnable` extraction for archives exceeding 10 MB.
- **Polkit D-Bus Helper & Isolation Package**:
  - Introduced `ThemeWriter` supporting both elevated Polkit and D-Bus helper service (`com.sddmthememanager.Helper`).
  - Created modular `sddm_theme_manager` package allowing isolated imports (`from sddm_theme_manager.install_dialog import InstallDialog`).
- **Comprehensive Test Suite Expansion**:
  - Test suite expanded from 206 to **248 automated tests** with 100% pass rate.

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
│   ├── preview.py                   # Manages sddm-greeter --test-mode subprocess & entry validation
│   ├── polkit.py                    # Elevated pkexec / sudo runner
│   ├── store_client.py              # KDE Store / Pling OCS API client
│   ├── desktop_wallpaper.py         # Multi-DE active wallpaper detector & synchronizer (Hyprland/GNOME/KDE)
│   ├── color_palette.py             # Dominant palette & Pywal color extractor
│   ├── video_background.py          # Animated & video wallpaper manager (MP4/WebM/GIF)
│   ├── theme_configurator.py        # Visual theme tweaker engine (clock, blur, dim, font)
│   ├── avatar_manager.py            # User profile login picture manager
│   ├── scheduler.py                 # Automated Day/Night theme switcher & systemd timer
│   ├── linter.py                    # Qt5/Qt6 compatibility scanner, entry validator & auto-patcher
│   ├── exporter.py                  # Portable theme bundle packager (.tar.gz/.tar.zst)
│   ├── display_manager.py           # Multi-monitor display detector & Xsetup configurator
│   ├── daemon_config.py             # SDDM daemon settings, autologin, & session manager
│   ├── theme_enhancer.py            # Universal Next-Gen feature injector & rollback engine
│   ├── live_daemon.py               # Real-time hardware telemetry, MPRIS & status daemon
│   ├── passkey_server.py            # Embedded HTTP REST API & mobile passkey auth server
│   ├── boot_shield.py               # Failsafe watchdog & crash recovery daemon
│   ├── ai_generator.py              # Prompt-to-Theme natural language AI ricing engine
│   ├── chameleon_presets.py         # OS Chameleon theme presets (macOS, Win11, Cyberpunk)
│   ├── marketplace.py               # Decentralized community theme catalog & publisher
│   ├── monetization.py              # Artist sponsorship & Supporter Pro Pass manager
│   ├── sticky_notes.py              # Pre-login household sticky notes manager
│   ├── system_hud.py                # Hardware telemetry HUD collector
│   ├── mpris_bridge.py              # MPRIS2 player discovery & media capsule bridge
│   ├── fido2_detector.py            # USB sysfs FIDO2/YubiKey hardware key detector
│   ├── ble_proximity.py             # Bluetooth Low Energy RSSI proximity scanner
│   ├── panic_mode.py                # Duress panic decoy sandbox & privacy auditor
│   ├── solar_timelapse.py           # 24-hour solar calculation & satellite imagery
│   └── greeter_games.py             # Embedded retro QML mini-games (Flappy Tux, Pong)
├── ui/
│   ├── main_window.py               # Main window, toolbar, status bar & live watcher
│   ├── install_dialog.py            # Dual-card chooser dialog (scaffold vs archive)
│   ├── theme_editor.py              # Multi-file code editor & debounced live preview dialog
│   ├── theme_enhancer_dialog.py     # Interactive Next-Gen feature equip & rollback modal
│   ├── theme_writer.py              # Polkit file writer, Qt 6 greeter template & wallpaper generator
│   ├── archive_installer.py         # Archive extraction, flattening, validation & backup
│   ├── theme_grid.py                # Scrollable card grid with filter & sort
│   ├── detail_panel.py              # Metadata panel & scrollable action tool buttons
│   ├── store_dialog.py              # KDE Store browser modal
│   ├── tweaker_dialog.py            # Interactive visual theme customizer dialog
│   ├── avatar_dialog.py             # Circular profile avatar cropping dialog
│   ├── scheduler_dialog.py          # Day/Night automated schedule dialog
│   ├── linter_dialog.py             # Theme compatibility report & auto-patcher modal
│   ├── display_dialog.py            # Primary monitor selection dialog
│   ├── daemon_dialog.py             # SDDM daemon autologin & session settings dialog
│   ├── boot_shield_dialog.py        # Boot Shield safety watchdog & crash recovery dialog
│   ├── sticky_notes_dialog.py       # Household pre-login sticky notes bulletin dialog
│   ├── chameleon_dialog.py          # OS Chameleon presets generator dialog
│   ├── ai_ricing_dialog.py          # Prompt-to-theme AI ricing studio modal
│   ├── security_dialog.py           # Passkey QR, FIDO2, Panic Mode & BLE security center
│   ├── marketplace_dialog.py        # Rice-Drop community marketplace & package publisher
│   ├── monetization_dialog.py       # Creator tips & Supporter Pro Pass dialog
│   ├── studio_builder.py            # Zero-Code WYSIWYG Drag-and-Drop Theme Studio
│   ├── preview_overlay.py           # Floating exit pill during live greeter preview
│   └── styles.qss                   # Modern DE-agnostic dark/light stylesheet
├── sddm_theme_manager/              # Isolated package for standalone imports
│   ├── __init__.py
│   ├── install_dialog.py
│   ├── theme_editor.py
│   ├── theme_writer.py
│   ├── archive_installer.py
│   ├── live_daemon.py
│   ├── sticky_notes_dialog.py
│   ├── chameleon_dialog.py
│   ├── ai_ricing_dialog.py
│   ├── security_dialog.py
│   ├── marketplace_dialog.py
│   ├── monetization_dialog.py
│   └── polkit/
│       ├── helper.py                # D-Bus service & CLI privileged helper
│       └── com.sddmthememanager.policy
├── polkit/
│   ├── 40-sddm-theme-manager.rules   # JavaScript Polkit rule file
│   ├── com.sddmthememanager.policy  # Polkit action definitions
│   └── helper.py                    # Elevated execution D-Bus service helper
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
