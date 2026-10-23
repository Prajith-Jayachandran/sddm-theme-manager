"""
SDDM Theme Manager - Theme Scanner
Discovers installed SDDM themes, parses metadata, detects active theme,
and resolves SDDM configuration priority.
"""

import configparser
import locale
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class Theme:
    id: str  # Folder name, e.g. "breeze"
    name: str  # Display name, e.g. "Breeze"
    description: str  # Comment / description
    path: Path  # Absolute folder path
    qt_version: str  # "6", "5", or "Unknown"
    theme_type: str = "sddm-theme"
    author: str = ""
    version: str = ""
    website: str = ""
    preview_path: Optional[Path] = None
    is_system: bool = False
    is_active: bool = False
    is_installed_in_system: bool = False
    is_missing_from_system: bool = False
    mtime: float = 0.0
    custom_background: Optional[str] = None
    default_background: Optional[str] = None

    @property
    def display_qt_version(self) -> str:
        if self.qt_version in ("5", "6"):
            return f"Qt {self.qt_version}"
        return self.qt_version or "Unknown"

    @property
    def location_badge(self) -> str:
        if self.is_system or self.is_installed_in_system:
            return "System"
        return "User"


class ThemeScanner:
    """Scans system and user paths for SDDM themes and resolves active theme."""

    SEARCH_PATHS = [
        Path("/usr/share/sddm/themes"),
        Path("/usr/local/share/sddm/themes"),
        Path.home() / ".local/share/sddm/themes",
    ]

    @classmethod
    def get_user_themes_dir(cls) -> Path:
        user_dir = Path.home() / ".local/share/sddm/themes"
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    @classmethod
    def get_active_theme_name(cls) -> str:
        """
        Resolves active theme from SDDM configurations in priority order:
        1. /etc/sddm.conf.d/*.conf (sorted lexicographically)
        2. /etc/sddm.conf
        3. ~/.config/sddm.conf
        """
        active_theme = ""

        # 1. Drop-ins in /etc/sddm.conf.d/
        dropin_dir = Path("/etc/sddm.conf.d")
        if dropin_dir.exists() and dropin_dir.is_dir():
            try:
                conf_files = sorted(dropin_dir.glob("*.conf"))
                for conf_file in conf_files:
                    theme_val = cls._read_theme_current_from_file(conf_file)
                    if theme_val:
                        active_theme = theme_val
            except Exception:
                pass

        if active_theme:
            return active_theme

        # 2. Main system config /etc/sddm.conf
        main_conf = Path("/etc/sddm.conf")
        if main_conf.exists() and main_conf.is_file():
            theme_val = cls._read_theme_current_from_file(main_conf)
            if theme_val:
                return theme_val

        # 3. User config ~/.config/sddm.conf
        user_conf = Path.home() / ".config/sddm.conf"
        if user_conf.exists() and user_conf.is_file():
            theme_val = cls._read_theme_current_from_file(user_conf)
            if theme_val:
                return theme_val

        return ""

    @staticmethod
    def _read_theme_current_from_file(filepath: Path) -> Optional[str]:
        """Reads Current= value under [Theme] from an INI file."""
        try:
            parser = configparser.ConfigParser(strict=False, interpolation=None)
            parser.optionxform = str
            parser.read(filepath, encoding="utf-8")
            if parser.has_section("Theme") and parser.has_option("Theme", "Current"):
                val = parser.get("Theme", "Current").strip()
                if val:
                    return val
        except Exception:
            # Fallback to simple line-by-line reading in case of invalid INI syntax
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    in_theme = False
                    for line in f:
                        line = line.strip()
                        if line.startswith("[") and line.endswith("]"):
                            in_theme = line.lower() == "[theme]"
                        elif in_theme and "=" in line:
                            k, v = line.split("=", 1)
                            if k.strip().lower() == "current":
                                return v.strip()
            except Exception:
                pass
        return None

    @classmethod
    def scan_themes(cls) -> List[Theme]:
        """Scans all search paths, parses metadata, and marks the active theme."""
        active_theme_id = cls.get_active_theme_name()
        themes_map: dict[str, Theme] = {}

        # Scan in order so user themes or earlier overrides can be indexed
        for base_path in cls.SEARCH_PATHS:
            if not base_path.exists() or not base_path.is_dir():
                continue

            try:
                entries = sorted(base_path.iterdir())
            except Exception:
                continue

            for entry in entries:
                if not entry.is_dir():
                    continue

                # Must look like an SDDM theme
                if not cls.is_valid_theme_dir(entry):
                    continue

                theme = cls.parse_theme_dir(entry)
                if theme:
                    if theme.id == active_theme_id:
                        theme.is_active = True
                    themes_map[str(theme.path)] = theme

        # Deduplicate themes sharing the same id (prioritize system installation)
        themes_by_id: dict[str, Theme] = {}
        for theme in themes_map.values():
            if theme.id not in themes_by_id:
                themes_by_id[theme.id] = theme
            else:
                existing = themes_by_id[theme.id]
                # Prioritize system installation over user directory copy
                if theme.is_system and not existing.is_system:
                    themes_by_id[theme.id] = theme
                elif not theme.is_system and existing.is_system:
                    continue
                elif theme.is_active and not existing.is_active:
                    themes_by_id[theme.id] = theme
                elif not existing.preview_path and theme.preview_path:
                    themes_by_id[theme.id] = theme
                elif theme.custom_background and not existing.custom_background:
                    themes_by_id[theme.id] = theme

        # Verify system installation status for all themes
        system_base = Path("/usr/share/sddm/themes")
        for theme in themes_by_id.values():
            sys_path = system_base / theme.id
            theme.is_installed_in_system = sys_path.exists() and sys_path.is_dir()
            # Flag if theme is set active in config but files are missing from system SDDM dir
            if theme.is_active and not theme.is_installed_in_system:
                theme.is_missing_from_system = True

        return list(themes_by_id.values())

    @staticmethod
    def is_valid_theme_dir(theme_dir: Path) -> bool:
        """Determines if a directory contains SDDM theme components."""
        indicators = [
            "metadata.desktop",
            "Main.qml",
            "main.qml",
            "theme.conf",
            "theme.conf.user",
        ]
        return any((theme_dir / ind).exists() for ind in indicators)

    @classmethod
    def parse_theme_dir(cls, theme_dir: Path) -> Optional[Theme]:
        """Parses a theme directory into a Theme object."""
        try:
            folder_id = theme_dir.name
            metadata_file = theme_dir / "metadata.desktop"

            name = folder_id.replace("-", " ").replace("_", " ").title()
            description = "SDDM Theme"
            qt_version = "6"  # modern default
            theme_type = "sddm-theme"
            author = ""
            version = ""
            website = ""

            # Check metadata.desktop
            if metadata_file.exists():
                meta_data = cls._parse_desktop_file(metadata_file)
                if "name" in meta_data and meta_data["name"]:
                    name = meta_data["name"]
                if "comment" in meta_data and meta_data["comment"]:
                    description = meta_data["comment"]
                if "qtversion" in meta_data and meta_data["qtversion"]:
                    qt_version = meta_data["qtversion"].strip()
                if "type" in meta_data and meta_data["type"]:
                    theme_type = meta_data["type"]
                if "author" in meta_data:
                    author = meta_data["author"]
                if "version" in meta_data:
                    version = meta_data["version"]
                if "website" in meta_data:
                    website = meta_data["website"]

            # Heuristics for Qt version if unknown or not found in desktop file
            if qt_version not in ("5", "6"):
                qt_version = cls._detect_qt_version_from_qml(theme_dir)

            # 1. Look for standard preview images
            preview_path = None
            for p_name in ["preview.png", "preview.jpg", "preview.jpeg", "preview.webp", "screenshot.png", "screenshot.jpg"]:
                cand = theme_dir / p_name
                if cand.exists() and cand.is_file():
                    preview_path = cand
                    break

            # 2. Look in screenshots/ directory
            if not preview_path and (theme_dir / "screenshots").exists():
                try:
                    for s_file in sorted((theme_dir / "screenshots").iterdir()):
                        if s_file.is_file() and s_file.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                            preview_path = s_file
                            break
                except Exception:
                    pass

            # 3. Read custom and default backgrounds (resolving relative paths against theme_dir)
            custom_bg = cls._read_conf_background(theme_dir / "theme.conf.user", theme_dir)
            default_bg = cls._read_conf_background(theme_dir / "theme.conf", theme_dir)

            # 4. Check for theme-named or standard background images
            if not preview_path:
                for img_cand in [
                    theme_dir / f"{folder_id}.jpg",
                    theme_dir / f"{folder_id}.png",
                    theme_dir / "background.jpg",
                    theme_dir / "background.png",
                    theme_dir / "images" / "background.png",
                    theme_dir / "images" / "background.jpg",
                ]:
                    if img_cand.exists() and img_cand.is_file():
                        preview_path = img_cand
                        break

            # 5. Check if effective background is an image or video
            effective_bg = custom_bg or default_bg
            if effective_bg and Path(effective_bg).exists():
                eff_path = Path(effective_bg)
                if not preview_path and eff_path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".svg"):
                    preview_path = eff_path
                elif not preview_path and eff_path.suffix.lower() in (".mp4", ".webm", ".mkv", ".mov"):
                    gen_thumb = cls._extract_video_thumbnail(eff_path, theme_dir)
                    if gen_thumb and gen_thumb.exists():
                        preview_path = gen_thumb

            # 6. Deep search across subdirectories (images/, backgrounds/, assets/, wallpapers/)
            if not preview_path:
                for sub_name in ["images", "backgrounds", "assets", "wallpapers"]:
                    sub_dir = theme_dir / sub_name
                    if sub_dir.exists() and sub_dir.is_dir():
                        try:
                            # Prefer largest image (likely background/preview)
                            cand_imgs = [
                                f for f in sub_dir.iterdir()
                                if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
                            ]
                            if cand_imgs:
                                cand_imgs.sort(key=lambda x: x.stat().st_size, reverse=True)
                                preview_path = cand_imgs[0]
                                break
                        except Exception:
                            pass

            # 7. Check for any video files in theme root if still no preview
            if not preview_path:
                for v_ext in (".mp4", ".webm", ".mkv", ".mov"):
                    for v_cand in theme_dir.glob(f"*{v_ext}"):
                        if v_cand.is_file():
                            gen_thumb = cls._extract_video_thumbnail(v_cand, theme_dir)
                            if gen_thumb and gen_thumb.exists():
                                preview_path = gen_thumb
                                break
                    if preview_path:
                        break

            # 8. Check for any image file in theme root (largest image preferred)
            if not preview_path:
                root_imgs = [
                    f for f in theme_dir.iterdir()
                    if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
                ]
                if root_imgs:
                    root_imgs.sort(key=lambda x: x.stat().st_size, reverse=True)
                    preview_path = root_imgs[0]

            mtime = 0.0
            try:
                mtime = theme_dir.stat().st_mtime
            except Exception:
                pass

            is_system = str(theme_dir.resolve()).startswith("/usr")

            return Theme(
                id=folder_id,
                name=name,
                description=description,
                path=theme_dir.resolve(),
                qt_version=qt_version,
                theme_type=theme_type,
                author=author,
                version=version,
                website=website,
                preview_path=preview_path,
                is_system=is_system,
                is_active=False,
                mtime=mtime,
                custom_background=custom_bg,
                default_background=default_bg,
            )
        except Exception as e:
            return None

    @staticmethod
    def _parse_desktop_file(filepath: Path) -> dict[str, str]:
        """Parses metadata.desktop adhering to locale preferences."""
        result: dict[str, str] = {}
        try:
            cur_locale, _ = locale.getlocale()
        except Exception:
            cur_locale = None
        lang = cur_locale.split("_")[0] if cur_locale else "en"

        current_section = ""
        localized_names: dict[str, str] = {}
        localized_comments: dict[str, str] = {}

        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line.startswith("[") and line.endswith("]"):
                        current_section = line[1:-1].strip()
                        continue

                    if "=" not in line:
                        continue

                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip()

                    key_lower = key.lower()
                    if key_lower == "name":
                        result["name"] = val
                    elif key_lower.startswith("name["):
                        loc_key = key[5:-1]
                        localized_names[loc_key] = val
                    elif key_lower in ("comment", "description"):
                        result["comment"] = val
                    elif key_lower.startswith("comment[") or key_lower.startswith("description["):
                        loc_key = key[key.find("[") + 1 : -1]
                        localized_comments[loc_key] = val
                    elif key_lower in ("qtversion", "x-plasma-api"):
                        result["qtversion"] = val
                    elif key_lower == "type":
                        result["type"] = val
                    elif key_lower in ("author", "x-kde-plugininfo-author"):
                        result["author"] = val
                    elif key_lower in ("version", "x-kde-plugininfo-version"):
                        result["version"] = val
                    elif key_lower in ("website", "x-kde-plugininfo-website"):
                        result["website"] = val
        except Exception:
            pass

        # Apply localization if available
        if lang in localized_names:
            result["name"] = localized_names[lang]
        if lang in localized_comments:
            result["comment"] = localized_comments[lang]

        return result

    @staticmethod
    def _detect_qt_version_from_qml(theme_dir: Path) -> str:
        """Inspects QML entry points to infer Qt5 or Qt6."""
        for qml_name in ["Main.qml", "main.qml"]:
            qml_path = theme_dir / qml_name
            if qml_path.exists():
                try:
                    content = qml_path.read_text(encoding="utf-8", errors="ignore")
                    if "import QtQuick 6" in content or "import QtCore 6" in content:
                        return "6"
                    if "import QtQuick 2" in content and "import QtQuick.Controls 1" in content:
                        return "5"
                    if "import QtQuick 2" in content and "import QtQuick.Controls 2" in content:
                        return "6"
                except Exception:
                    pass
        return "6"

    @staticmethod
    def _read_conf_background(conf_path: Path, theme_dir: Optional[Path] = None) -> Optional[str]:
        """Reads background= value under [General] in theme.conf or theme.conf.user."""
        if not conf_path.exists():
            return None
        bg = None
        try:
            parser = configparser.ConfigParser(strict=False, interpolation=None)
            parser.optionxform = str
            parser.read(conf_path, encoding="utf-8")
            if parser.has_section("General") and parser.has_option("General", "background"):
                bg = parser.get("General", "background").strip()
        except Exception:
            pass

        if not bg:
            try:
                with open(conf_path, "r", encoding="utf-8", errors="ignore") as f:
                    in_general = False
                    for line in f:
                        line = line.strip()
                        if line.startswith("[") and line.endswith("]"):
                            in_general = line.lower() == "[general]"
                        elif in_general and "=" in line:
                            k, v = line.split("=", 1)
                            if k.strip().lower() == "background":
                                bg = v.strip()
                                break
            except Exception:
                pass

        if bg and theme_dir is not None:
            bg_path = Path(bg)
            if not bg_path.is_absolute():
                bg_path = theme_dir / bg_path
            return str(bg_path.resolve())
        elif bg:
            return bg

        return None

    @staticmethod
    def _extract_video_thumbnail(video_path: Path, theme_dir: Path) -> Optional[Path]:
        """Extracts a thumbnail frame from a video background using ffmpeg."""
        import shutil, subprocess
        if not shutil.which("ffmpeg"):
            return None
        try:
            target_out = theme_dir / "preview.png"
            if not os.access(theme_dir, os.W_OK):
                cache_dir = Path.home() / ".cache" / "sddm_previews"
                cache_dir.mkdir(parents=True, exist_ok=True)
                target_out = cache_dir / f"{theme_dir.name}_preview.png"

            if target_out.exists() and target_out.stat().st_size > 0:
                return target_out

            subprocess.run(
                ["ffmpeg", "-y", "-ss", "00:00:00.5", "-i", str(video_path), "-vframes", "1", str(target_out)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            if target_out.exists() and target_out.stat().st_size > 0:
                return target_out
        except Exception:
            pass
        return None
