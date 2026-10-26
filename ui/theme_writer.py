"""
SDDM Theme Manager - Polkit-Aware Theme Writer
Handles writes to system and user theme directories using D-Bus helper / polkit.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional, Tuple

from core.polkit import restart_sddm_service, write_file_privileged

logger = logging.getLogger("sddm_theme_manager.theme_writer")

DBUS_BUS_NAME = "com.sddmthememanager.Helper"
DBUS_OBJECT_PATH = "/com/sddmthememanager/Helper"
DBUS_INTERFACE = "com.sddmthememanager.Helper"


class ThemeWriter:
    """Polkit-aware file writer and theme scaffold manager."""

    @classmethod
    def is_privileged_path(cls, path: str | Path) -> bool:
        """Determines if writing to the specified path requires root privileges."""
        p = Path(path).resolve()
        if str(p).startswith("/usr") or str(p).startswith("/etc"):
            return True
        # Find closest existing parent directory to check write permissions
        curr = p
        while not curr.exists() and curr != curr.parent:
            curr = curr.parent
        return not os.access(curr, os.W_OK)

    @classmethod
    def write_file(cls, path: str | Path, content: str) -> Tuple[bool, str]:
        """
        Writes text content to a destination file.
        Uses direct filesystem write for user paths (~/.local/share/...) and
        elevated polkit D-Bus / pkexec for system paths (/usr/share/...).
        """
        target = Path(path).resolve()

        if not cls.is_privileged_path(target):
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                return True, "File written successfully."
            except Exception as e:
                return False, f"Failed to write user file: {e}"

        # Privileged path: Try D-Bus helper first if available
        try:
            import dbus

            bus = dbus.SystemBus()
            proxy = bus.get_object(DBUS_BUS_NAME, DBUS_OBJECT_PATH)
            helper = dbus.Interface(proxy, DBUS_INTERFACE)
            ok, msg = helper.WriteFile(str(target), content)
            if ok:
                return True, str(msg)
        except Exception:
            # Fall back to pkexec / sudo wrapper
            pass

        return write_file_privileged(target, content)

    @classmethod
    def restart_sddm(cls) -> Tuple[bool, str]:
        """Restarts SDDM display manager via D-Bus helper or pkexec systemctl."""
        try:
            import dbus

            bus = dbus.SystemBus()
            proxy = bus.get_object(DBUS_BUS_NAME, DBUS_OBJECT_PATH)
            helper = dbus.Interface(proxy, DBUS_INTERFACE)
            ok, msg = helper.RestartSDDM()
            if ok:
                return True, str(msg)
        except Exception:
            pass

        return restart_sddm_service()

    @classmethod
    def scaffold_theme(
        cls,
        theme_name: str,
        base_dir: Optional[Path | str] = None,
    ) -> Tuple[bool, Optional[Path], str]:
        """
        Scaffolds a new SDDM theme in /usr/share/sddm/themes/<name>/ (or base_dir):
        - Creates directory
        - starter theme.conf
        - empty metadata.json
        - metadata.desktop
        """
        dest_base = Path(base_dir) if base_dir else Path("/usr/share/sddm/themes")
        theme_dir = dest_base / theme_name

        starter_conf = (
            "[General]\n"
            "background=\n"
            "type=image\n"
            "font=\n"
        )

        metadata_json = json.dumps(
            {"name": theme_name, "author": "", "version": "1.0", "description": ""},
            indent=2,
        )

        metadata_desktop = (
            "[SddmGreeterTheme]\n"
            f"Name={theme_name}\n"
            "Description=Custom SDDM Theme\n"
            "Author=\n"
            "Version=1.0\n"
            "MainScript=Main.qml\n"
            "ConfigFile=theme.conf\n"
            "QtVersion=6\n"
        )

        # Write theme.conf
        ok, msg = cls.write_file(theme_dir / "theme.conf", starter_conf)
        if not ok:
            return False, None, f"Failed to scaffold theme.conf: {msg}"

        # Write metadata.json
        ok, msg = cls.write_file(theme_dir / "metadata.json", metadata_json)
        if not ok:
            return False, None, f"Failed to scaffold metadata.json: {msg}"

        # Write metadata.desktop
        ok, msg = cls.write_file(theme_dir / "metadata.desktop", metadata_desktop)
        if not ok:
            return False, None, f"Failed to scaffold metadata.desktop: {msg}"

        return True, theme_dir, f"Theme '{theme_name}' scaffolded successfully at {theme_dir}."
