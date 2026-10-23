"""
SDDM Theme Manager - Animated & Video Wallpaper Support
Manages looping video and animated GIF backgrounds for compatible SDDM themes.
Generates static thumbnail frames for cards and greeter fallbacks.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

from PySide6.QtGui import QImage, QImageReader

from .polkit import copy_file_privileged, run_command, write_file_privileged


class VideoBackgroundManager:
    """Manages video and animated wallpapers (MP4, WebM, MKV, GIF)."""

    SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mkv", ".mov", ".gif"}

    @classmethod
    def is_video(cls, file_path: Path | str) -> bool:
        """Returns True if the file extension is a supported video/animated format."""
        return Path(file_path).suffix.lower() in cls.SUPPORTED_VIDEO_EXTENSIONS

    @classmethod
    def extract_poster_frame(cls, video_path: Path, output_image_path: Path) -> bool:
        """
        Extracts a static poster frame from video/GIF using ffmpeg or QImageReader.
        """
        v_path = Path(video_path).resolve()
        out_path = Path(output_image_path).resolve()

        # If it's a GIF, use native QImageReader
        if v_path.suffix.lower() == ".gif":
            reader = QImageReader(str(v_path))
            if reader.canRead():
                img = reader.read()
                if not img.isNull():
                    return img.save(str(out_path), "PNG")

        # Try ffmpeg / ffmpegthumbnailer
        ffmpeg_bin = shutil.which("ffmpeg")
        if ffmpeg_bin:
            try:
                cmd = [
                    ffmpeg_bin,
                    "-y",
                    "-ss",
                    "00:00:01",
                    "-i",
                    str(v_path),
                    "-vframes",
                    "1",
                    "-q:v",
                    "2",
                    str(out_path),
                ]
                res = subprocess.run(cmd, capture_output=True, timeout=5)
                if res.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0:
                    return True
            except Exception:
                pass

        # Try ffmpegthumbnailer
        thumb_bin = shutil.which("ffmpegthumbnailer")
        if thumb_bin:
            try:
                cmd = [thumb_bin, "-i", str(v_path), "-o", str(out_path), "-s", "512", "-q", "8"]
                res = subprocess.run(cmd, capture_output=True, timeout=5)
                if res.returncode == 0 and out_path.exists():
                    return True
            except Exception:
                pass

        return False

    @classmethod
    def _update_conf_with_video(cls, original_text: str, video_path: str) -> str:
        """Helper to set background, backgroundVideo, videoBackground and type in [General]."""
        lines = original_text.splitlines() if original_text else []
        updated_lines = []
        in_general = False
        general_found = False

        entries_to_set = {
            "background": video_path,
            "backgroundVideo": video_path,
            "videoBackground": video_path,
            "type": "video",
        }
        written_keys = set()

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                if in_general:
                    for k, v in entries_to_set.items():
                        if k.lower() not in written_keys:
                            updated_lines.append(f"{k}={v}")
                            written_keys.add(k.lower())
                    in_general = False

                if stripped.lower() == "[general]":
                    in_general = True
                    general_found = True

            elif in_general and "=" in stripped:
                k, _ = stripped.split("=", 1)
                k_clean = k.strip()
                matched = False
                for target_k, target_v in entries_to_set.items():
                    if k_clean.lower() == target_k.lower():
                        updated_lines.append(f"{target_k}={target_v}")
                        written_keys.add(target_k.lower())
                        matched = True
                        break
                if matched:
                    continue

            updated_lines.append(line)

        if in_general:
            for k, v in entries_to_set.items():
                if k.lower() not in written_keys:
                    updated_lines.append(f"{k}={v}")
                    written_keys.add(k.lower())

        if not general_found:
            if updated_lines and updated_lines[-1] != "":
                updated_lines.append("")
            updated_lines.append("[General]")
            for k, v in entries_to_set.items():
                updated_lines.append(f"{k}={v}")

        return "\n".join(updated_lines).strip() + "\n"

    @classmethod
    def set_video_background(cls, theme_dir: Path, video_path: Path | str) -> Tuple[bool, str]:
        """
        Sets the animated/video background in both theme.conf and theme.conf.user.
        Copies the video file to theme directory if needed to ensure sddm user readability.
        """
        v_path = Path(video_path).resolve()
        if not v_path.exists() or not v_path.is_file():
            return False, f"Video file does not exist: {v_path}"

        if not cls.is_video(v_path):
            return False, f"Unsupported video format: {v_path.suffix}"

        theme_p = Path(theme_dir).resolve()
        is_system = str(theme_p).startswith("/usr")
        theme_conf = theme_p / "theme.conf"
        theme_orig = theme_p / "theme.conf.orig"
        user_conf = theme_p / "theme.conf.user"

        written_path = str(v_path)

        if is_system:
            # If the source video is inside a user folder, copy it into theme directory
            dest_vid = theme_p / f"custom_background{v_path.suffix.lower()}"
            cp_ok, _ = copy_file_privileged(v_path, dest_vid)
            if cp_ok:
                run_command(["/usr/bin/chmod", "0644", str(dest_vid)], privileged=True)
                written_path = str(dest_vid)

            # Handle themes that hardcode 'bg.mp4' (e.g., star-rail)
            target_bg_mp4 = theme_p / "bg.mp4"
            if target_bg_mp4.exists():
                bg_orig = theme_p / "bg.mp4.orig"
                if not bg_orig.exists():
                    copy_file_privileged(target_bg_mp4, bg_orig)
                copy_file_privileged(v_path, target_bg_mp4)
                run_command(["/usr/bin/chmod", "0644", str(target_bg_mp4)], privileged=True)
        else:
            target_bg_mp4 = theme_p / "bg.mp4"
            if target_bg_mp4.exists():
                bg_orig = theme_p / "bg.mp4.orig"
                if not bg_orig.exists():
                    shutil.copy2(target_bg_mp4, bg_orig)
                shutil.copy2(v_path, target_bg_mp4)

        # Backup theme.conf if not already backed up
        if theme_conf.exists() and not theme_orig.exists():
            orig_text = theme_conf.read_text(encoding="utf-8", errors="ignore")
            if is_system:
                write_file_privileged(theme_orig, orig_text)
            else:
                theme_orig.write_text(orig_text, encoding="utf-8")

        # 1. Update theme.conf.user
        orig_user = user_conf.read_text(encoding="utf-8", errors="ignore") if user_conf.exists() else ""
        new_user = cls._update_conf_with_video(orig_user, written_path)

        # 2. Update theme.conf
        orig_conf = theme_conf.read_text(encoding="utf-8", errors="ignore") if theme_conf.exists() else ""
        new_conf = cls._update_conf_with_video(orig_conf, written_path)

        if is_system:
            write_file_privileged(user_conf, new_user)
            ok, msg = write_file_privileged(theme_conf, new_conf)
        else:
            try:
                user_conf.write_text(new_user, encoding="utf-8")
                theme_conf.write_text(new_conf, encoding="utf-8")
                ok, msg = True, "Video wallpaper applied successfully."
            except Exception as e:
                ok, msg = False, str(e)

        if ok:
            # Extract poster frame to preview.png
            poster_dest = theme_p / "preview.png"
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = Path(tmp.name)
            try:
                if cls.extract_poster_frame(v_path, tmp_path):
                    if is_system:
                        copy_file_privileged(tmp_path, poster_dest)
                        run_command(["/usr/bin/chmod", "0644", str(poster_dest)], privileged=True)
                    else:
                        shutil.copy2(tmp_path, poster_dest)
            finally:
                tmp_path.unlink(missing_ok=True)

        return ok, msg
