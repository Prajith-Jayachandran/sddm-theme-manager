#!/usr/bin/env python3
"""
SDDM Theme Manager - D-Bus Polkit Helper Service
Provides com.sddmthememanager.Helper service on the system bus for privileged writes and service restarts.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

INTERFACE_NAME = "com.sddmthememanager.Helper"
BUS_NAME = "com.sddmthememanager.Helper"
OBJECT_PATH = "/com/sddmthememanager/Helper"

ALLOWED_PREFIXES = (
    "/usr/share/sddm/themes/",
    "/etc/sddm.conf",
    "/etc/sddm.conf.d/",
)


class HelperService:
    """Core helper implementation for privileged actions."""

    @staticmethod
    def is_path_allowed(path_str: str) -> bool:
        resolved = str(Path(path_str).resolve())
        return any(resolved.startswith(prefix) or resolved == prefix.rstrip("/") for prefix in ALLOWED_PREFIXES)

    @classmethod
    def write_file(cls, path_str: str, content: str) -> tuple[bool, str]:
        if not cls.is_path_allowed(path_str):
            return False, f"Path '{path_str}' is outside allowed system locations."

        target = Path(path_str).resolve()
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            os.chmod(target, 0o644)
            return True, "File written successfully."
        except Exception as e:
            return False, str(e)

    @staticmethod
    def restart_sddm() -> tuple[bool, str]:
        systemctl = shutil.which("systemctl") or "/usr/bin/systemctl"
        try:
            res = subprocess.run([systemctl, "restart", "sddm"], capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                return True, "SDDM restarted successfully."
            return False, res.stderr or res.stdout or f"Failed with exit code {res.returncode}"
        except Exception as e:
            return False, str(e)


def run_dbus_service():
    """Runs the service on the system D-Bus."""
    try:
        import dbus
        import dbus.service
        from dbus.mainloop.glib import DBusGMainLoop
        from gi.repository import GLib

        DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()

        class DBusHelper(dbus.service.Object):
            def __init__(self):
                bus_name = dbus.service.BusName(BUS_NAME, bus)
                super().__init__(bus_name, OBJECT_PATH)

            @dbus.service.method(INTERFACE_NAME, in_signature="ss", out_signature="bs")
            def WriteFile(self, path, content):
                return HelperService.write_file(str(path), str(content))

            @dbus.service.method(INTERFACE_NAME, in_signature="", out_signature="bs")
            def RestartSDDM(self):
                return HelperService.restart_sddm()

        _service = DBusHelper()
        loop = GLib.MainLoop()
        loop.run()
    except Exception as e:
        print(f"Failed to start D-Bus helper: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--dbus":
        run_dbus_service()
    elif len(sys.argv) >= 4 and sys.argv[1] == "write":
        ok, msg = HelperService.write_file(sys.argv[2], sys.argv[3])
        print(msg)
        sys.exit(0 if ok else 1)
    elif len(sys.argv) >= 2 and sys.argv[1] == "restart":
        ok, msg = HelperService.restart_sddm()
        print(msg)
        sys.exit(0 if ok else 1)
    else:
        print("Usage: helper.py [--dbus | write <path> <content> | restart]")
        sys.exit(1)
