"""
SDDM Theme Manager - Desktop Wallpaper Detection & Sync
Detects the active wallpaper from various Desktop Environments / Window Managers:
KDE Plasma, GNOME, Hyprland, Sway, XFCE, Feh, Nitrogen, and fallback sources.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from .background import BackgroundManager


class DesktopWallpaperDetector:
    """Detects active desktop wallpaper from popular Linux environments."""

    @classmethod
    def detect_wallpaper(cls) -> Optional[Path]:
        """
        Attempts to find the current desktop wallpaper from desktop environment configs.
        Returns Path to image if found and valid, otherwise None.
        """
        detectors = [
            cls._detect_plasma,
            cls._detect_hyprland,
            cls._detect_sway,
            cls._detect_gnome,
            cls._detect_feh,
            cls._detect_nitrogen,
            cls._detect_xfce,
            cls._detect_plasma_default_fallback,
        ]

        for detector in detectors:
            try:
                path = detector()
                if path and path.is_file() and path.exists():
                    return path
            except Exception:
                continue

        return None

    @classmethod
    def _detect_plasma(cls) -> Optional[Path]:
        """Reads KDE Plasma wallpaper config from desktop-appletsrc."""
        config_path = Path.home() / ".config" / "plasma-org.kde.plasma.desktop-appletsrc"
        if not config_path.exists():
            return None

        content = config_path.read_text(encoding="utf-8", errors="ignore")
        # Match Image=file:///... or Image=/path/... or usersWallpapers=...
        matches = re.findall(r"^(?:Image|usersWallpapers)=(?:file://)?([^\r\n]+)", content, re.MULTILINE)
        if matches:
            for candidate in reversed(matches):
                clean_path = candidate.strip().split(",")[0]  # usersWallpapers can be a comma list
                p = Path(clean_path)
                if p.is_file() and p.exists():
                    return p
                # Might be a wallpaper package directory containing contents/images/
                if p.is_dir():
                    images_dir = p / "contents" / "images"
                    if images_dir.exists():
                        imgs = sorted(images_dir.glob("*.png")) + sorted(images_dir.glob("*.jpg"))
                        if imgs:
                            return imgs[-1]
        return None

    @classmethod
    def _detect_plasma_default_fallback(cls) -> Optional[Path]:
        """KDE default wallpaper fallback if no custom wallpaper was configured."""
        candidates = [
            Path("/usr/share/wallpapers/Next/contents/images/5120x2880.png"),
            Path("/usr/share/wallpapers/Next/contents/images/1920x1080.png"),
            Path("/usr/share/wallpapers/Next/contents/images/2560x1600.png"),
        ]
        for c in candidates:
            if c.exists():
                return c
        return None

    @classmethod
    def _detect_hyprland(cls) -> Optional[Path]:
        """Detects wallpaper on Hyprland via swww or hyprpaper."""
        # 1. Try swww
        if shutil.which("swww"):
            try:
                res = subprocess.run(["swww", "query"], capture_output=True, text=True, timeout=1)
                if res.returncode == 0:
                    # e.g.: "DP-1: /path/to/image.png"
                    match = re.search(r":\s*([/\w\.\-\s]+\.(?:png|jpg|jpeg|webp))", res.stdout, re.IGNORECASE)
                    if match:
                        p = Path(match.group(1).strip())
                        if p.exists():
                            return p
            except Exception:
                pass

        # 2. Try hyprpaper config
        hyprpaper_conf = Path.home() / ".config" / "hypr" / "hyprpaper.conf"
        if hyprpaper_conf.exists():
            content = hyprpaper_conf.read_text(encoding="utf-8", errors="ignore")
            match = re.search(r"wallpaper\s*=\s*[^,]+,\s*([/\w\.\-\s]+)", content)
            if match:
                p = Path(match.group(1).strip())
                if p.exists():
                    return p
        return None

    @classmethod
    def _detect_sway(cls) -> Optional[Path]:
        """Detects wallpaper from sway config."""
        sway_conf = Path.home() / ".config" / "sway" / "config"
        if sway_conf.exists():
            content = sway_conf.read_text(encoding="utf-8", errors="ignore")
            match = re.search(r"output\s+\S+\s+bg\s+([/\w\.\-\s]+)\s+fill", content)
            if match:
                p = Path(match.group(1).strip())
                if p.exists():
                    return p
        return None

    @classmethod
    def _detect_gnome(cls) -> Optional[Path]:
        """Reads GNOME wallpaper setting via gsettings."""
        if not shutil.which("gsettings"):
            return None
        for schema_key in ["picture-uri", "picture-uri-dark"]:
            try:
                res = subprocess.run(
                    ["gsettings", "get", "org.gnome.desktop.background", schema_key],
                    capture_output=True,
                    text=True,
                    timeout=1,
                )
                if res.returncode == 0 and res.stdout.strip():
                    uri = res.stdout.strip().strip("'\"")
                    if uri.startswith("file://"):
                        uri = uri[7:]
                    p = Path(uri)
                    if p.exists() and p.is_file():
                        return p
            except Exception:
                continue
        return None

    @classmethod
    def _detect_feh(cls) -> Optional[Path]:
        """Reads feh startup command from ~/.fehbg."""
        fehbg = Path.home() / ".fehbg"
        if fehbg.exists():
            content = fehbg.read_text(encoding="utf-8", errors="ignore")
            match = re.search(r"feh\s+.*?'([^']+)'", content) or re.search(r"feh\s+.*?([/\w\.\-\s]+\.(?:png|jpg|jpeg|webp))", content)
            if match:
                p = Path(match.group(1).strip())
                if p.exists():
                    return p
        return None

    @classmethod
    def _detect_nitrogen(cls) -> Optional[Path]:
        """Reads nitrogen config from ~/.config/nitrogen/bg-saved.cfg."""
        nitro = Path.home() / ".config" / "nitrogen" / "bg-saved.cfg"
        if nitro.exists():
            content = nitro.read_text(encoding="utf-8", errors="ignore")
            match = re.search(r"file=([/\w\.\-\s]+)", content)
            if match:
                p = Path(match.group(1).strip())
                if p.exists():
                    return p
        return None

    @classmethod
    def _detect_xfce(cls) -> Optional[Path]:
        """Reads xfce wallpaper via xfconf-query."""
        if not shutil.which("xfconf-query"):
            return None
        try:
            res = subprocess.run(
                ["xfconf-query", "-c", "xfce4-desktop", "-p", "/backdrop/screen0/monitor0/workspace0/last-image"],
                capture_output=True,
                text=True,
                timeout=1,
            )
            if res.returncode == 0 and res.stdout.strip():
                p = Path(res.stdout.strip())
                if p.exists():
                    return p
        except Exception:
            pass
        return None

    @classmethod
    def sync_desktop_to_theme(cls, theme_dir: Path) -> Tuple[bool, str]:
        """
        Detects desktop wallpaper and applies it to the specified theme directory.
        """
        wp = cls.detect_wallpaper()
        if not wp:
            return False, "Could not detect active desktop wallpaper."
        ok, msg = BackgroundManager.set_background(theme_dir, wp)
        if ok:
            return True, f"Successfully synced desktop wallpaper ({wp.name}) to SDDM theme."
        return False, f"Failed to sync wallpaper: {msg}"
