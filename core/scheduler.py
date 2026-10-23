"""
SDDM Theme Manager - Day / Night Theme Scheduler
Manages automatic theme switching between day and night themes via systemd user timers.
"""

import datetime
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from .theme_applier import ThemeApplier
from .theme_scanner import ThemeScanner


class DayNightScheduler:
    """Configures and runs day/night automated theme switching."""

    CONFIG_PATH = Path.home() / ".config" / "sddm-theme-manager" / "scheduler.json"
    SYSTEMD_USER_DIR = Path.home() / ".config" / "systemd" / "user"

    DEFAULT_CONFIG = {
        "enabled": False,
        "day_theme": "breeze",
        "night_theme": "breeze",
        "day_time": "07:00",
        "night_time": "19:00",
    }

    @classmethod
    def read_config(cls) -> dict:
        """Reads scheduler config or returns defaults."""
        if not cls.CONFIG_PATH.exists():
            return dict(cls.DEFAULT_CONFIG)
        try:
            data = json.loads(cls.CONFIG_PATH.read_text(encoding="utf-8"))
            merged = dict(cls.DEFAULT_CONFIG)
            merged.update(data)
            return merged
        except Exception:
            return dict(cls.DEFAULT_CONFIG)

    @classmethod
    def save_config(cls, cfg: dict) -> Tuple[bool, str]:
        """Saves scheduler configuration to user config directory."""
        cls.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            cls.CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
            if cfg.get("enabled", False):
                cls.install_systemd_units(cfg.get("day_time", "07:00"), cfg.get("night_time", "19:00"))
            else:
                cls.remove_systemd_units()
            return True, "Scheduler configuration saved."
        except Exception as e:
            return False, f"Failed to save scheduler config: {e}"

    @classmethod
    def install_systemd_units(cls, day_time: str, night_time: str) -> Tuple[bool, str]:
        """Installs and enables systemd user timer and service."""
        cls.SYSTEMD_USER_DIR.mkdir(parents=True, exist_ok=True)

        service_path = cls.SYSTEMD_USER_DIR / "sddm-theme-scheduler.service"
        timer_path = cls.SYSTEMD_USER_DIR / "sddm-theme-scheduler.timer"

        # Determine launcher path
        app_bin = Path.home() / ".local" / "bin" / "sddm-theme-manager"
        exec_path = str(app_bin) if app_bin.exists() else (shutil.which("sddm-theme-manager") or "sddm-theme-manager")

        service_content = f"""[Unit]
Description=SDDM Theme Manager Day/Night Scheduled Switcher
After=network.target

[Service]
Type=oneshot
ExecStart={exec_path} --apply-scheduled
"""

        timer_content = f"""[Unit]
Description=SDDM Theme Manager Day/Night Timer

[Timer]
OnCalendar=*-*-* {day_time}:00
OnCalendar=*-*-* {night_time}:00
Persistent=true

[Install]
WantedBy=timers.target
"""

        try:
            service_path.write_text(service_content, encoding="utf-8")
            timer_path.write_text(timer_content, encoding="utf-8")

            if shutil.which("systemctl"):
                subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True, timeout=3)
                subprocess.run(["systemctl", "--user", "enable", "--now", "sddm-theme-scheduler.timer"], capture_output=True, timeout=3)
            return True, "Systemd timer activated."
        except Exception as e:
            return False, f"Failed to install systemd timer: {e}"

    @classmethod
    def remove_systemd_units(cls) -> Tuple[bool, str]:
        """Disables and removes systemd user timer."""
        timer_path = cls.SYSTEMD_USER_DIR / "sddm-theme-scheduler.timer"
        service_path = cls.SYSTEMD_USER_DIR / "sddm-theme-scheduler.service"

        if shutil.which("systemctl"):
            try:
                subprocess.run(["systemctl", "--user", "stop", "sddm-theme-scheduler.timer"], capture_output=True, timeout=3)
                subprocess.run(["systemctl", "--user", "disable", "sddm-theme-scheduler.timer"], capture_output=True, timeout=3)
                subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True, timeout=3)
            except Exception:
                pass

        timer_path.unlink(missing_ok=True)
        service_path.unlink(missing_ok=True)
        return True, "Scheduler timer disabled."

    @classmethod
    def apply_scheduled(cls, force: bool = False, custom_cfg: Optional[dict] = None) -> Tuple[bool, str]:
        """
        Determines whether day or night theme is active right now and applies it.
        If force=True, applies the current time slot even if scheduler is not enabled.
        """
        cfg = custom_cfg or cls.read_config()
        if not force and not cfg.get("enabled", False):
            return False, "Day/Night scheduler is not enabled."

        now = datetime.datetime.now().time()
        try:
            dh, dm = map(int, cfg.get("day_time", "07:00").split(":"))
            nh, nm = map(int, cfg.get("night_time", "19:00").split(":"))
            d_time = datetime.time(dh, dm)
            n_time = datetime.time(nh, nm)
        except Exception:
            d_time = datetime.time(7, 0)
            n_time = datetime.time(19, 0)

        # Check if day or night
        if d_time <= n_time:
            is_day = (d_time <= now < n_time)
        else:
            is_day = (now >= d_time or now < n_time)

        target_theme = cfg.get("day_theme") if is_day else cfg.get("night_theme")
        if not target_theme:
            return False, "No theme configured for current time window."

        # Find target theme
        themes = ThemeScanner.scan_themes()
        target = next((t for t in themes if t.id == target_theme or t.name == target_theme), None)
        if not target:
            return False, f"Target theme '{target_theme}' not found on system."

        return ThemeApplier.apply_theme(target)
