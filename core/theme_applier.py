"""
SDDM Theme Manager - Theme Applier
Applies an SDDM theme by updating or creating the drop-in configuration
/etc/sddm.conf.d/10-theme.conf, ensuring the theme is installed to
/usr/share/sddm/themes/ so SDDM system daemon can load it on boot.
"""

import configparser
import io
import os
import shutil
from pathlib import Path
from typing import List, Optional, Tuple, Union

from .polkit import restart_sddm_service, run_command, write_file_privileged

DROPIN_CONF_PATH = Path("/etc/sddm.conf.d/10-theme.conf")
SYSTEM_THEMES_DIR = Path("/usr/share/sddm/themes")


class ThemeApplier:
    """Manages applying SDDM themes via drop-in configuration files and syncing system files."""

    @classmethod
    def sync_theme_to_system(cls, theme_path: Path, theme_id: str) -> Tuple[bool, str]:
        """
        Copies a theme from user space (~/.local/share/sddm/themes/) to the system
        SDDM directory (/usr/share/sddm/themes/) with world-readable permissions
        so the sddm daemon can display it on the login screen.
        """
        src_path = Path(theme_path).resolve()
        if not src_path.exists():
            return False, f"Theme source directory does not exist: {src_path}"

        # 1. Normalize permissions in user space first so files copy with clean read permissions
        try:
            for root, dirs, files in os.walk(src_path):
                for d in dirs:
                    try:
                        os.chmod(os.path.join(root, d), 0o755)
                    except Exception:
                        pass
                for f in files:
                    try:
                        os.chmod(os.path.join(root, f), 0o644)
                    except Exception:
                        pass
        except Exception:
            pass

        # 2. Copy recursively to /usr/share/sddm/themes/
        cp_bin = shutil.which("cp") or "/usr/bin/cp"
        rc, out, err = run_command([cp_bin, "-r", str(src_path), str(SYSTEM_THEMES_DIR) + "/"], privileged=True)
        if rc != 0:
            return False, f"Failed to copy theme to /usr/share/sddm/themes/: {err or out}"

        # 3. Ensure permissions with chmod (non-blocking fallback)
        dest_path = SYSTEM_THEMES_DIR / theme_id
        chmod_bin = shutil.which("chmod") or "/usr/bin/chmod"
        run_command([chmod_bin, "-R", "a+rX", str(dest_path)], privileged=True, timeout=5)

        # 4. Verify system installation actually succeeded
        if not dest_path.exists() or not dest_path.is_dir():
            return False, f"Verification failed: Theme was not found at {dest_path} after copy."

        # Check for essential theme files
        has_essential = any(
            (dest_path / f).exists()
            for f in ["metadata.desktop", "Main.qml", "main.qml", "theme.conf"]
        )
        if not has_essential:
            return False, f"Verification failed: {dest_path} is missing standard SDDM theme files."

        return True, f"Theme '{theme_id}' successfully installed into /usr/share/sddm/themes/."

    @classmethod
    def apply_theme(cls, theme_obj_or_id: Union[str, object]) -> Tuple[bool, str]:
        """
        Sets Current=<theme_id> under [Theme] in /etc/sddm.conf.d/10-theme.conf.
        Ensures the theme exists in /usr/share/sddm/themes/ so SDDM doesn't fall back
        to the default theme on reboot.
        """
        theme_id = ""
        theme_path: Optional[Path] = None

        if hasattr(theme_obj_or_id, "id") and hasattr(theme_obj_or_id, "path"):
            theme_id = str(theme_obj_or_id.id).strip()
            theme_path = Path(theme_obj_or_id.path).resolve()
        elif isinstance(theme_obj_or_id, str):
            theme_id = theme_obj_or_id.strip()
            # Try to resolve path from ~/.local/share/sddm/themes/<theme_id>
            user_cand = Path.home() / ".local/share/sddm/themes" / theme_id
            if user_cand.exists():
                theme_path = user_cand.resolve()
            else:
                sys_cand = SYSTEM_THEMES_DIR / theme_id
                if sys_cand.exists():
                    theme_path = sys_cand.resolve()

        if not theme_id:
            return False, "Theme identifier cannot be empty."

        # If theme is outside /usr/share/sddm/themes OR not yet present in /usr/share/sddm/themes,
        # copy/sync it to the system directory
        system_dest = SYSTEM_THEMES_DIR / theme_id
        needs_sync = False
        if theme_path and not str(theme_path).startswith("/usr/share/sddm/themes"):
            needs_sync = True
        elif not system_dest.exists():
            needs_sync = True

        if needs_sync:
            if not theme_path or not theme_path.exists():
                # Attempt to find it in user themes
                cand = Path.home() / ".local/share/sddm/themes" / theme_id
                if cand.exists():
                    theme_path = cand

            if theme_path and theme_path.exists():
                sync_ok, sync_msg = cls.sync_theme_to_system(theme_path, theme_id)
                if not sync_ok:
                    return False, f"Could not sync theme to SDDM system folder: {sync_msg}"
            else:
                return False, f"Theme directory for '{theme_id}' could not be located to sync to /usr/share/sddm/themes/."

        # Write drop-in configuration /etc/sddm.conf.d/10-theme.conf
        new_content = cls._generate_config_content(theme_id)
        success, msg = write_file_privileged(DROPIN_CONF_PATH, new_content)
        if success:
            return True, f"Theme '{theme_id}' successfully applied to {DROPIN_CONF_PATH} and verified in {SYSTEM_THEMES_DIR}."
        else:
            return False, f"Failed to write configuration: {msg}"

    @classmethod
    def sync_all_user_themes(cls) -> Tuple[int, int, List[str]]:
        """
        Synchronizes all themes in ~/.local/share/sddm/themes/ to /usr/share/sddm/themes/.
        Returns (success_count, error_count, list_of_messages).
        """
        user_dir = Path.home() / ".local/share/sddm/themes"
        if not user_dir.exists():
            return 0, 0, ["No user themes directory found."]

        successes = 0
        errors = 0
        messages = []

        for entry in sorted(user_dir.iterdir()):
            if not entry.is_dir():
                continue
            has_files = any((entry / f).exists() for f in ["metadata.desktop", "Main.qml", "main.qml", "theme.conf"])
            if not has_files:
                continue

            ok, msg = cls.sync_theme_to_system(entry, entry.name)
            if ok:
                successes += 1
                messages.append(f"✓ {entry.name}: Synced")
            else:
                errors += 1
                messages.append(f"✗ {entry.name}: {msg}")

        return successes, errors, messages

    @classmethod
    def check_active_theme_health(cls) -> Tuple[bool, str, Optional[str]]:
        """
        Verifies if the currently configured SDDM theme exists in /usr/share/sddm/themes/.
        Returns (is_healthy, status_message, active_theme_name).
        """
        # Read active theme from SDDM configurations
        active_theme = ""
        if DROPIN_CONF_PATH.exists():
            try:
                parser = configparser.ConfigParser(strict=False, interpolation=None)
                parser.optionxform = str
                parser.read(DROPIN_CONF_PATH, encoding="utf-8")
                if parser.has_section("Theme") and parser.has_option("Theme", "Current"):
                    active_theme = parser.get("Theme", "Current").strip()
            except Exception:
                pass

        if not active_theme:
            return True, "No custom SDDM theme configured.", None

        sys_theme_dir = SYSTEM_THEMES_DIR / active_theme
        if not sys_theme_dir.exists() or not sys_theme_dir.is_dir():
            user_theme_dir = Path.home() / ".local/share/sddm/themes" / active_theme
            if user_theme_dir.exists():
                return (
                    False,
                    f"Theme '{active_theme}' is set as active, but missing from /usr/share/sddm/themes/. "
                    f"It is available in user storage and needs to be synced.",
                    active_theme,
                )
            else:
                return (
                    False,
                    f"Theme '{active_theme}' is set as active, but not found on the system.",
                    active_theme,
                )

        return True, f"Active theme '{active_theme}' is installed in {SYSTEM_THEMES_DIR}.", active_theme

    @classmethod
    def restart_sddm(cls) -> Tuple[bool, str]:
        """Restarts the SDDM systemd service via elevated privileges."""
        return restart_sddm_service()

    @classmethod
    def _generate_config_content(cls, theme_id: str) -> str:
        """
        Reads existing config from /etc/sddm.conf.d/10-theme.conf if present,
        updates [Theme] -> Current, and returns the formatted text.
        """
        parser = configparser.ConfigParser(strict=False, interpolation=None)
        parser.optionxform = str

        if DROPIN_CONF_PATH.exists():
            try:
                parser.read(DROPIN_CONF_PATH, encoding="utf-8")
            except Exception:
                pass

        if not parser.has_section("Theme"):
            parser.add_section("Theme")

        parser.set("Theme", "Current", theme_id)

        buffer = io.StringIO()
        parser.write(buffer)
        content = buffer.getvalue().strip() + "\n"
        return content
