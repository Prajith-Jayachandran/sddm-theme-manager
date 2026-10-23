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

        theme_p = Path(theme_dir).resolve()
        is_system = str(theme_p).startswith("/usr")

        # Determine path to write into theme configuration
        # If theme is in /usr and source image is in user's home (mode 0700),
        # SDDM daemon (user sddm, uid 952) cannot read it. Copy into theme dir.
        written_bg_path = str(img_p)
        if is_system and not str(img_p).startswith("/usr/share/"):
            dest_bg = theme_p / f"custom_background{img_p.suffix.lower()}"
            from .polkit import copy_file_privileged, run_command
            cp_ok, cp_msg = copy_file_privileged(img_p, dest_bg)
            if cp_ok:
                run_command(["/usr/bin/chmod", "0644", str(dest_bg)], privileged=True)
                written_bg_path = str(dest_bg)

        # 1. Update theme.conf.user (legacy / user override)
        theme_user_conf = theme_p / "theme.conf.user"
        user_content = cls._update_background_in_conf(theme_user_conf, written_bg_path)

        # 2. Update theme.conf directly (the actual config file SDDM greeters load)
        theme_conf = theme_p / "theme.conf"
        theme_orig = theme_p / "theme.conf.orig"

        # Backup original theme.conf on first modification
        if theme_conf.exists() and not theme_orig.exists():
            orig_text = theme_conf.read_text(encoding="utf-8", errors="ignore")
            if is_system:
                write_file_privileged(theme_orig, orig_text)
            else:
                theme_orig.write_text(orig_text, encoding="utf-8")

        conf_content = cls._update_background_in_conf(theme_conf, written_bg_path)

        if is_system:
            write_file_privileged(theme_user_conf, user_content)
            ok, msg = write_file_privileged(theme_conf, conf_content)
            return ok, msg
        else:
            try:
                theme_user_conf.write_text(user_content, encoding="utf-8")
                theme_conf.write_text(conf_content, encoding="utf-8")
                return True, "Background set successfully."
            except Exception as e:
                return False, f"Failed to write theme configuration: {e}"

    @classmethod
    def reset_background(cls, theme_dir: Path) -> Tuple[bool, str]:
        """
        Resets custom background to theme default by restoring theme.conf.orig,
        cleaning up copied custom background files, and removing theme.conf.user.
        """
        theme_p = Path(theme_dir).resolve()
        is_system = str(theme_p).startswith("/usr")
        theme_conf = theme_p / "theme.conf"
        theme_orig = theme_p / "theme.conf.orig"
        theme_user_conf = theme_p / "theme.conf.user"

        # Restore original theme.conf if present
        if theme_orig.exists():
            orig_text = theme_orig.read_text(encoding="utf-8", errors="ignore")
            if is_system:
                write_file_privileged(theme_conf, orig_text)
                remove_path_privileged(theme_orig)
            else:
                theme_conf.write_text(orig_text, encoding="utf-8")
                theme_orig.unlink(missing_ok=True)

        # Clean up any custom_background.* in theme folder
        for custom_bg in theme_p.glob("custom_background.*"):
            if is_system:
                remove_path_privileged(custom_bg)
            else:
                custom_bg.unlink(missing_ok=True)

        if not theme_user_conf.exists() and not theme_orig.exists():
            return True, "Theme is already using default background."

        if theme_user_conf.exists():
            parser = configparser.ConfigParser(strict=False, interpolation=None)
            parser.optionxform = str
            try:
                parser.read(theme_user_conf, encoding="utf-8")
            except Exception:
                parser = configparser.ConfigParser()

            # Remove background option from [General]
            if parser.has_section("General") and parser.has_option("General", "background"):
                parser.remove_option("General", "background")
                if not parser.options("General"):
                    parser.remove_section("General")

            # If parser has no remaining sections or options, delete the file
            has_remaining = any(len(parser.options(sec)) > 0 for sec in parser.sections())
            if not has_remaining:
                if is_system:
                    remove_path_privileged(theme_user_conf)
                else:
                    theme_user_conf.unlink(missing_ok=True)
            else:
                # Write back remaining settings
                buf = io.StringIO()
                parser.write(buf)
                new_content = buf.getvalue().strip() + "\n"
                if is_system:
                    write_file_privileged(theme_user_conf, new_content)
                else:
                    theme_user_conf.write_text(new_content, encoding="utf-8")

        return True, "Theme background reset to default."

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
