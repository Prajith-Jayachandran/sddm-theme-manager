"""
SDDM Theme Manager - Background / Wallpaper Manager
Manages custom wallpaper overrides via theme.conf.user inside the theme directory.
"""

import configparser
import io
import os
from pathlib import Path
from typing import Optional, Tuple

from .polkit import remove_path_privileged, write_file_privileged


class BackgroundManager:
    """Manages theme.conf.user background overrides for SDDM themes."""

    SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".bmp", ".gif", ".mp4", ".webm", ".mkv"}

    @classmethod
    def set_background(cls, theme_dir: Path, image_path: Path | str) -> Tuple[bool, str]:
        """
        Sets the custom background image or video for a theme in theme.conf.user.
        Preserves other keys and sections in theme.conf.user.
        """
        img_p = Path(image_path).resolve()
        if not img_p.exists() or not img_p.is_file():
            return False, f"Image file does not exist: {img_p}"

        if img_p.suffix.lower() not in cls.SUPPORTED_EXTENSIONS:
            return False, f"Unsupported image format: {img_p.suffix}. Supported: {', '.join(sorted(cls.SUPPORTED_EXTENSIONS))}"

        # Delegate video formats to VideoBackgroundManager
        from .video_background import VideoBackgroundManager
        if VideoBackgroundManager.is_video(img_p):
            return VideoBackgroundManager.set_video_background(theme_dir, img_p)

        # Ensure image has world-read permissions so SDDM user can read it
        try:
            cur_mode = img_p.stat().st_mode
            if not (cur_mode & 0o004):  # not world-readable
                os.chmod(img_p, cur_mode | 0o644)
        except Exception:
            pass

        theme_user_conf = theme_dir / "theme.conf.user"
        new_content = cls._update_background_in_conf(theme_user_conf, str(img_p))

        is_system = str(theme_dir.resolve()).startswith("/usr")
        if is_system:
            return write_file_privileged(theme_user_conf, new_content)
        else:
            try:
                theme_user_conf.write_text(new_content, encoding="utf-8")
                return True, "Background set successfully."
            except Exception as e:
                return False, f"Failed to write theme.conf.user: {e}"

    @classmethod
    def reset_background(cls, theme_dir: Path) -> Tuple[bool, str]:
        """
        Resets custom background to theme default by removing background key from
        theme.conf.user or deleting theme.conf.user if no other keys remain.
        """
        theme_user_conf = theme_dir / "theme.conf.user"
        if not theme_user_conf.exists():
            return True, "Theme is already using default background."

        parser = configparser.ConfigParser(strict=False, interpolation=None)
        parser.optionxform = str
        try:
            parser.read(theme_user_conf, encoding="utf-8")
        except Exception:
            parser = configparser.ConfigParser()

        # Remove background option from [General]
        if parser.has_section("General") and parser.has_option("General", "background"):
            parser.remove_option("General", "background")
            # If [General] section is empty now, remove it
            if not parser.options("General"):
                parser.remove_section("General")

        is_system = str(theme_dir.resolve()).startswith("/usr")

        # If parser has no remaining sections or options, delete the file
        has_remaining = any(len(parser.options(sec)) > 0 for sec in parser.sections())
        if not has_remaining:
            if is_system:
                return remove_path_privileged(theme_user_conf)
            else:
                try:
                    theme_user_conf.unlink(missing_ok=True)
                    return True, "Custom background removed. Theme reset to default."
                except Exception as e:
                    return False, f"Failed to delete theme.conf.user: {e}"
        else:
            # Write back remaining settings
            buf = io.StringIO()
            parser.write(buf)
            new_content = buf.getvalue().strip() + "\n"
            if is_system:
                return write_file_privileged(theme_user_conf, new_content)
            else:
                try:
                    theme_user_conf.write_text(new_content, encoding="utf-8")
                    return True, "Background reset; preserved other custom settings."
                except Exception as e:
                    return False, f"Failed to update theme.conf.user: {e}"

    @classmethod
    def get_current_background(cls, theme_dir: Path) -> Optional[str]:
        """
        Returns the effective background image path for a theme,
        checking theme.conf.user first, then theme.conf.
        """
        for conf_name in ["theme.conf.user", "theme.conf"]:
            conf_path = theme_dir / conf_name
            if conf_path.exists():
                try:
                    parser = configparser.ConfigParser(strict=False, interpolation=None)
                    parser.optionxform = str
                    parser.read(conf_path, encoding="utf-8")
                    if parser.has_section("General") and parser.has_option("General", "background"):
                        bg = parser.get("General", "background").strip()
                        if bg:
                            # If relative path, resolve relative to theme_dir
                            bg_path = Path(bg)
                            if not bg_path.is_absolute():
                                bg_path = theme_dir / bg_path
                            return str(bg_path)
                except Exception:
                    pass
        return None

    @staticmethod
    def _update_background_in_conf(conf_path: Path, image_path: str) -> str:
        """Reads existing theme.conf.user if present, sets background, returns content string."""
        parser = configparser.ConfigParser(strict=False, interpolation=None)
        parser.optionxform = str
        if conf_path.exists():
            try:
                parser.read(conf_path, encoding="utf-8")
            except Exception:
                pass

        if not parser.has_section("General"):
            parser.add_section("General")

        parser.set("General", "background", image_path)

        buf = io.StringIO()
        parser.write(buf)
        return buf.getvalue().strip() + "\n"
