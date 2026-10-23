"""
SDDM Theme Manager - Animated & Video Wallpaper Support
Manages looping video and animated GIF backgrounds for compatible SDDM themes.
Generates static thumbnail frames for cards and greeter fallbacks.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from PySide6.QtGui import QImage, QImageReader

from .polkit import write_file_privileged


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
                # Seek to 1 second and grab 1 frame
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
    def set_video_background(cls, theme_dir: Path, video_path: Path | str) -> Tuple[bool, str]:
        """
        Sets the animated/video background in theme.conf.user.
        """
        v_path = Path(video_path).resolve()
        if not v_path.exists() or not v_path.is_file():
            return False, f"Video file does not exist: {v_path}"

        if not cls.is_video(v_path):
            return False, f"Unsupported video format: {v_path.suffix}"

        # Ensure world-read permissions
        try:
            cur_mode = v_path.stat().st_mode
            if not (cur_mode & 0o004):
                os.chmod(v_path, cur_mode | 0o644)
        except Exception:
            pass

        theme_p = Path(theme_dir).resolve()
        user_conf = theme_p / "theme.conf.user"

        lines = []
        if user_conf.exists():
            lines = user_conf.read_text(encoding="utf-8", errors="ignore").splitlines()

        # Update or add background, backgroundVideo, and videoBackground in [General]
        updated_lines = []
        in_general = False
        general_found = False
        bg_set = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                if in_general:
                    if not bg_set:
                        updated_lines.append(f"background={v_path}")
                        updated_lines.append(f"backgroundVideo={v_path}")
                        updated_lines.append(f"videoBackground={v_path}")
                        bg_set = True
                    in_general = False

                if stripped.lower() == "[general]":
                    in_general = True
                    general_found = True

            elif in_general and "=" in stripped:
                k, _ = stripped.split("=", 1)
                k_clean = k.strip().lower()
                if k_clean in ("background", "backgroundvideo", "videobackground"):
                    updated_lines.append(f"{k.strip()}={v_path}")
                    bg_set = True
                    continue

            updated_lines.append(line)

        if in_general and not bg_set:
            updated_lines.append(f"background={v_path}")
            updated_lines.append(f"backgroundVideo={v_path}")
            updated_lines.append(f"videoBackground={v_path}")
            bg_set = True

        if not general_found:
            updated_lines.append("")
            updated_lines.append("[General]")
            updated_lines.append(f"background={v_path}")
            updated_lines.append(f"backgroundVideo={v_path}")
            updated_lines.append(f"videoBackground={v_path}")

        new_content = "\n".join(updated_lines).strip() + "\n"

        is_system = str(theme_p).startswith("/usr")
        if is_system:
            ok, msg = write_file_privileged(user_conf, new_content)
        else:
            try:
                user_conf.write_text(new_content, encoding="utf-8")
                ok, msg = True, "Video wallpaper applied successfully."
            except Exception as e:
                ok, msg = False, str(e)

        if ok:
            # Also generate a static thumbnail next to user_conf if possible
            poster_dest = theme_p / "preview.png"
            if not poster_dest.exists():
                cls.extract_poster_frame(v_path, poster_dest)

        return ok, msg
