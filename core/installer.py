"""
SDDM Theme Manager - Theme Installer & Remover
Handles archive extraction (.tar.gz, .zip, etc.) to ~/.local/share/sddm/themes/
and safe removal of user and system themes.
"""

import os
import re
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Optional, Tuple

from .polkit import remove_path_privileged
from .theme_scanner import ThemeScanner

SUPPORTED_ARCHIVES = (".tar.gz", ".tgz", ".tar.bz2", ".tar.xz", ".tar", ".zip")


class ThemeInstaller:
    """Installs themes from archives into user themes directory and manages uninstallation."""

    @classmethod
    def install_from_archive(
        cls,
        archive_path: Path | str,
        dest_base: Optional[Path | str] = None,
    ) -> Tuple[bool, Optional[Path], str]:
        """
        Extracts a theme archive directly into /usr/share/sddm/themes/ (or custom dest_base).
        Returns (success, installed_theme_path, message).
        """
        arch = Path(archive_path).resolve()
        if not arch.exists() or not arch.is_file():
            return False, None, f"Archive file does not exist: {arch}"

        suffix = arch.name.lower()
        is_supported = any(suffix.endswith(ext) for ext in SUPPORTED_ARCHIVES)
        if not is_supported:
            return False, None, f"Unsupported archive format. Supported formats: {', '.join(SUPPORTED_ARCHIVES)}"

        dest_dir = Path(dest_base) if dest_base is not None else Path("/usr/share/sddm/themes")
        is_system_dest = str(dest_dir).startswith("/usr")

        with tempfile.TemporaryDirectory(prefix="sddm_theme_extract_") as temp_dir:
            temp_path = Path(temp_dir)

            # 1. Extract archive to temp directory
            try:
                if arch.suffix.lower() == ".zip":
                    with zipfile.ZipFile(arch, "r") as zf:
                        zf.extractall(temp_path)
                else:
                    with tarfile.open(arch, "r:*") as tf:
                        # Prevent path traversal vulnerabilities
                        for member in tf.getmembers():
                            target = temp_path / member.name
                            if not target.resolve().is_relative_to(temp_path.resolve()):
                                return False, None, "Archive contains malicious path traversal components."
                        tf.extractall(temp_path)
            except Exception as e:
                return False, None, f"Failed to extract archive: {e}"

            # 2. Locate the actual theme directory inside extracted files
            theme_source_dir = cls._locate_theme_root(temp_path)
            if not theme_source_dir:
                return False, None, "Archive does not appear to contain a valid SDDM theme (missing metadata.desktop, Main.qml, or theme.conf)."

            # 3. Determine theme destination folder name
            target_name = theme_source_dir.name
            if target_name == temp_path.name or target_name == "sddm-theme-master" or target_name == "src":
                # Derive folder name from archive name
                clean_name = arch.name
                for ext in sorted(SUPPORTED_ARCHIVES, key=len, reverse=True):
                    if clean_name.lower().endswith(ext):
                        clean_name = clean_name[: -len(ext)]
                        break
                target_name = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", clean_name).strip("._")
                if not target_name:
                    target_name = "installed-theme"

            final_dest = dest_dir / target_name

            # 4. Pre-normalize permissions inside the temp directory
            try:
                for root, dirs, files in os.walk(theme_source_dir):
                    for d in dirs:
                        try:
                            os.chmod(os.path.join(root, d), 0o755)
                        except Exception:
                            pass
                    for f in files:
                        try:
                            os.chmod(os.path.join(root, f), 0o644)
                        except Exception:
                            pass
            except Exception:
                pass

            # 5. Ensure theme has a preview.png inside temp directory
            cls._ensure_preview_exists(theme_source_dir)

            # 6. Move extracted theme to destination
            if is_system_dest:
                from .polkit import copy_directory_privileged
                if final_dest.exists():
                    remove_path_privileged(final_dest)

                cp_ok, cp_msg = copy_directory_privileged(theme_source_dir, final_dest)
                if not cp_ok:
                    return False, None, f"Failed to install theme to {final_dest}: {cp_msg}"

                # Purge any legacy user copy so only one copy exists
                user_copy = ThemeScanner.get_user_themes_dir() / target_name
                if user_copy.exists():
                    shutil.rmtree(user_copy, ignore_errors=True)
            else:
                if final_dest.exists():
                    try:
                        shutil.rmtree(final_dest)
                    except Exception as e:
                        return False, None, f"Cannot overwrite existing theme directory '{final_dest.name}': {e}"
                try:
                    shutil.copytree(theme_source_dir, final_dest)
                except Exception as e:
                    return False, None, f"Failed to install theme files to {final_dest}: {e}"

            # 7. Verify final destination has theme files
            if not ThemeScanner.is_valid_theme_dir(final_dest):
                if is_system_dest:
                    remove_path_privileged(final_dest)
                else:
                    shutil.rmtree(final_dest, ignore_errors=True)
                return False, None, "Installed files do not form a valid SDDM theme."

            return True, final_dest, f"Theme '{final_dest.name}' installed successfully into {dest_dir}."

    @classmethod
    def _ensure_preview_exists(cls, theme_dir: Path):
        """Ensures the theme directory has a preview image for visual selector cards."""
        for p in ["preview.png", "preview.jpg", "preview.jpeg", "preview.webp", "screenshot.png", "screenshot.jpg"]:
            if (theme_dir / p).exists():
                return

        # Check screenshots/ directory
        if (theme_dir / "screenshots").exists():
            try:
                for s in sorted((theme_dir / "screenshots").iterdir()):
                    if s.is_file() and s.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                        shutil.copy2(s, theme_dir / "preview.png")
                        return
            except Exception:
                pass

        # Check theme.conf background setting
        conf_file = theme_dir / "theme.conf"
        if conf_file.exists():
            try:
                import configparser
                cp = configparser.ConfigParser(strict=False, interpolation=None)
                cp.read(conf_file, encoding="utf-8")
                if cp.has_section("General") and cp.has_option("General", "background"):
                    bg = cp.get("General", "background").strip()
                    bg_p = Path(bg)
                    if not bg_p.is_absolute():
                        bg_p = theme_dir / bg_p
                    if bg_p.exists():
                        if bg_p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                            shutil.copy2(bg_p, theme_dir / "preview.png")
                            return
                        elif bg_p.suffix.lower() in (".mp4", ".webm", ".mkv", ".mov"):
                            cls._extract_video_frame(bg_p, theme_dir / "preview.png")
                            return
            except Exception:
                pass

        # Check for any standard wallpaper files in theme root
        for img_name in [f"{theme_dir.name}.jpg", f"{theme_dir.name}.png", "background.jpg", "background.png", "images/background.png", "images/background.jpg"]:
            cand = theme_dir / img_name
            if cand.exists():
                try:
                    shutil.copy2(cand, theme_dir / "preview.png")
                    return
                except Exception:
                    pass

        # Check subdirectories images/, backgrounds/, assets/, wallpapers/
        for sub_name in ["images", "backgrounds", "assets", "wallpapers"]:
            sub_dir = theme_dir / sub_name
            if sub_dir.exists() and sub_dir.is_dir():
                try:
                    cand_imgs = [f for f in sub_dir.iterdir() if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")]
                    if cand_imgs:
                        cand_imgs.sort(key=lambda x: x.stat().st_size, reverse=True)
                        shutil.copy2(cand_imgs[0], theme_dir / "preview.png")
                        return
                except Exception:
                    pass

        # Check for any video files in root
        for v_ext in (".mp4", ".webm", ".mkv", ".mov"):
            for v_cand in theme_dir.glob(f"*{v_ext}"):
                if v_cand.is_file():
                    cls._extract_video_frame(v_cand, theme_dir / "preview.png")
                    if (theme_dir / "preview.png").exists():
                        return

        # Fallback: Generate a high-resolution preview.png if theme has no image files
        cls._generate_placeholder_preview(theme_dir)

    @classmethod
    def _generate_placeholder_preview(cls, theme_dir: Path):
        """Generates a high-resolution preview.png if theme has no image files."""
        out_path = theme_dir / "preview.png"
        if out_path.exists():
            return
        try:
            from PySide6.QtGui import QImage, QPainter, QLinearGradient, QColor, QPen, QGuiApplication
            from PySide6.QtCore import QRect, Qt
            theme_name = theme_dir.name.replace("-", " ").replace("_", " ").title()
            image = QImage(800, 450, QImage.Format_ARGB32_Premultiplied)
            image.fill(QColor(26, 27, 38))
            painter = QPainter(image)
            gradient = QLinearGradient(0, 0, 800, 450)
            gradient.setColorAt(0.0, QColor(36, 40, 59))
            gradient.setColorAt(1.0, QColor(26, 27, 38))
            painter.fillRect(QRect(0, 0, 800, 450), gradient)

            painter.setPen(QPen(QColor(65, 72, 104), 2))
            painter.drawRoundedRect(QRect(40, 30, 720, 390), 12, 12)

            if QGuiApplication.instance():
                from PySide6.QtGui import QFont
                painter.setPen(QColor(192, 202, 245))
                font = QFont("sans-serif", 24)
                font.setBold(True)
                painter.setFont(font)
                painter.drawText(QRect(0, 160, 800, 50), Qt.AlignCenter, theme_name[:24])

                painter.setPen(QColor(122, 162, 247))
                font_sub = QFont("sans-serif", 16)
                painter.setFont(font_sub)
                painter.drawText(QRect(0, 220, 800, 40), Qt.AlignCenter, "SDDM Greeter Theme")

            painter.end()

            image.save(str(out_path), "PNG")
        except Exception:
            pass

    @staticmethod
    def _extract_video_frame(video_path: Path, output_path: Path):
        """Extracts a frame from a video file into preview.png."""
        import subprocess
        if shutil.which("ffmpeg"):
            try:
                subprocess.run(
                    ["ffmpeg", "-y", "-ss", "00:00:00.5", "-i", str(video_path), "-vframes", "1", str(output_path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                )
            except Exception:
                pass

    @classmethod
    def remove_theme(cls, theme_path: Path | str) -> Tuple[bool, str]:
        """
        Removes a theme directory.
        Removes from /usr/share/sddm/themes/ (elevated) AND also checks and purges
        any corresponding legacy copy in ~/.local/share/sddm/themes/ so no duplicates linger.
        """
        t_path = Path(theme_path).resolve()
        theme_name = t_path.name
        is_system = str(t_path).startswith("/usr")

        # 1. Remove the targeted directory
        if is_system:
            success, msg = remove_path_privileged(t_path)
            if not success:
                return False, f"Failed to remove system theme '{theme_name}': {msg}"
        else:
            try:
                shutil.rmtree(t_path)
            except Exception as e:
                return False, f"Failed to remove user theme '{theme_name}': {e}"

        # 2. Always clean up corresponding copies in both places
        # Clean user copy if it exists
        user_copy = ThemeScanner.get_user_themes_dir() / theme_name
        if user_copy.exists():
            shutil.rmtree(user_copy, ignore_errors=True)

        # Clean system copy if it exists
        sys_copy = Path("/usr/share/sddm/themes") / theme_name
        if sys_copy.exists():
            remove_path_privileged(sys_copy)

        return True, f"Theme '{theme_name}' removed completely from system."

    @classmethod
    def _locate_theme_root(cls, root_dir: Path) -> Optional[Path]:
        """
        Traverses extracted directory to find the directory containing SDDM theme files.
        """
        if ThemeScanner.is_valid_theme_dir(root_dir):
            return root_dir

        # Check subdirectories up to 2 levels deep
        candidates = []
        for path in root_dir.glob("*"):
            if path.is_dir() and ThemeScanner.is_valid_theme_dir(path):
                candidates.append(path)

        if candidates:
            return candidates[0]

        for path in root_dir.glob("*/*"):
            if path.is_dir() and ThemeScanner.is_valid_theme_dir(path):
                candidates.append(path)

        if candidates:
            return candidates[0]

        for path in root_dir.glob("*/*/*"):
            if path.is_dir() and ThemeScanner.is_valid_theme_dir(path):
                candidates.append(path)

        if candidates:
            return candidates[0]

        return None
