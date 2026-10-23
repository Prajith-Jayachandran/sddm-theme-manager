"""
SDDM Theme Manager - Multi-Monitor Display Manager
Detects connected displays (via xrandr and DRM sysfs) and configures
the primary display in /usr/share/sddm/scripts/Xsetup so greeters appear on the right screen.
"""

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from .polkit import run_command, write_file_privileged


@dataclass
class MonitorInfo:
    name: str
    connected: bool
    is_primary: bool
    current_mode: Optional[str] = None
    available_modes: List[str] = None

    def __post_init__(self):
        if self.available_modes is None:
            self.available_modes = []


class DisplayManager:
    """Detects displays and configures SDDM primary monitor in Xsetup."""

    XSETUP_PATH = Path("/usr/share/sddm/scripts/Xsetup")

    @classmethod
    def get_connected_monitors(cls) -> List[MonitorInfo]:
        """
        Parses output from xrandr or /sys/class/drm to list connected monitors.
        """
        monitors: List[MonitorInfo] = []

        # Try xrandr
        if shutil.which("xrandr"):
            try:
                res = subprocess.run(["xrandr", "--query"], capture_output=True, text=True, timeout=2)
                if res.returncode == 0:
                    current_monitor = None
                    for line in res.stdout.splitlines():
                        m_match = re.match(r"^(\S+)\s+(connected|disconnected)\s*(primary)?\s*(.*)", line)
                        if m_match:
                            name, status, primary_tag, rest = m_match.groups()
                            is_conn = (status == "connected")
                            is_prim = bool(primary_tag)
                            current_mode = None
                            mode_match = re.search(r"(\d+x\d+)\+\d+\+\d+", rest)
                            if mode_match:
                                current_mode = mode_match.group(1)

                            current_monitor = MonitorInfo(
                                name=name,
                                connected=is_conn,
                                is_primary=is_prim,
                                current_mode=current_mode,
                                available_modes=[],
                            )
                            if is_conn:
                                monitors.append(current_monitor)
                        elif current_monitor and current_monitor.connected:
                            mode_line = re.match(r"^\s+(\d+x\d+)", line)
                            if mode_line:
                                mode_val = mode_line.group(1)
                                if mode_val not in current_monitor.available_modes:
                                    current_monitor.available_modes.append(mode_val)
                    if monitors:
                        return monitors
            except Exception:
                pass

        # DRM sysfs fallback (Wayland / headless)
        drm_path = Path("/sys/class/drm")
        if drm_path.exists():
            for card in drm_path.glob("card*-*"):
                status_file = card / "status"
                if status_file.exists():
                    try:
                        status = status_file.read_text(encoding="utf-8").strip()
                        if status == "connected":
                            name = card.name.split("-", 1)[1] if "-" in card.name else card.name
                            monitors.append(MonitorInfo(
                                name=name,
                                connected=True,
                                is_primary=False,
                                current_mode=None,
                                available_modes=[],
                            ))
                    except Exception:
                        continue

        if not monitors:
            monitors.append(MonitorInfo(name="Default Display", connected=True, is_primary=True))

        return monitors

    WAYLAND_DISPLAY_CONF = Path("/etc/sddm.conf.d/10-display.conf")

    @classmethod
    def set_primary_monitor(cls, output_name: str, mode: Optional[str] = None) -> Tuple[bool, str]:
        """
        Configures primary monitor across both X11 (via Xsetup) and Wayland (via 10-display.conf).
        """
        line_cmd = f"xrandr --output {output_name} --primary"
        if mode:
            line_cmd += f" --mode {mode}"

        current_content = ""
        if cls.XSETUP_PATH.exists():
            current_content = cls.XSETUP_PATH.read_text(encoding="utf-8", errors="ignore")

        # Strip any existing sddm-theme-manager xrandr primary block
        lines = []
        for l in current_content.splitlines():
            if "xrandr --output" in l and "--primary" in l:
                continue
            lines.append(l)

        if not lines or not lines[0].startswith("#!"):
            lines.insert(0, "#!/bin/sh")

        lines.append("")
        lines.append("# Set primary display for SDDM (configured by SDDM Theme Manager)")
        lines.append(line_cmd)

        new_content = "\n".join(lines).strip() + "\n"

        # 1. Update X11 Xsetup
        ok_x, msg_x = write_file_privileged(cls.XSETUP_PATH, new_content)
        if ok_x:
            run_command(["/usr/bin/chmod", "0755", str(cls.XSETUP_PATH)], privileged=True)

        # 2. Update Wayland drop-in config
        wayland_content = (
            "# Primary display for SDDM Wayland greeter (configured by SDDM Theme Manager)\n"
            "[Wayland]\n"
            f"PrimaryDisplay={output_name}\n"
        )
        ok_w, msg_w = write_file_privileged(cls.WAYLAND_DISPLAY_CONF, wayland_content)

        if ok_x or ok_w:
            return True, f"Primary monitor set to '{output_name}' for SDDM."
        return False, msg_x or msg_w

    @classmethod
    def get_configured_primary(cls) -> Optional[str]:
        """Checks if a primary monitor was configured in Xsetup or 10-display.conf."""
        if cls.WAYLAND_DISPLAY_CONF.exists():
            try:
                content = cls.WAYLAND_DISPLAY_CONF.read_text(encoding="utf-8", errors="ignore")
                for line in content.splitlines():
                    if line.strip().lower().startswith("primarydisplay="):
                        return line.split("=", 1)[1].strip()
            except Exception:
                pass

        if not cls.XSETUP_PATH.exists():
            return None
        content = cls.XSETUP_PATH.read_text(encoding="utf-8", errors="ignore")
        match = re.search(r"xrandr\s+--output\s+(\S+)\s+--primary", content)
        if match:
            return match.group(1)
        return None
