"""
SDDM Theme Manager - Archive Installer Module
Handles archive extraction, folder flattening, conflict resolution with backups,
and INI validation for SDDM themes.
"""

import configparser
import datetime
import os
import re
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Callable, Optional, Tuple

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import QMessageBox, QWidget

from core.installer import SUPPORTED_ARCHIVES, ThemeInstaller
from core.polkit import copy_directory_privileged, remove_path_privileged, run_command
from core.theme_scanner import ThemeScanner

SYSTEM_THEMES_DIR = Path("/usr/share/sddm/themes")
USER_THEMES_DIR = Path.home() / ".local/share/sddm/themes"


def derive_theme_name(archive_path: Path | str) -> str:
    """
    Derives a clean theme directory name from an archive file name.
    e.g. 'star-rail-v2.zip' -> 'star-rail-v2'
    """
    path = Path(archive_path)
    name = path.name
    for ext in sorted(SUPPORTED_ARCHIVES, key=len, reverse=True):
        if name.lower().endswith(ext):
            name = name[: -len(ext)]
            break

    sanitized = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", name).strip("._")
    return sanitized if sanitized else "installed-theme"


def validate_theme_conf(conf_path: Path | str) -> Tuple[bool, str]:
    """
    Validates that theme.conf exists and is parseable INI.
    Returns (is_valid, error_message_or_ok).
    Reports line number on syntax error.
    """
    p = Path(conf_path)
    if not p.exists() or not p.is_file():
        return False, f"theme.conf not found at {p}"

    try:
        content = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return False, f"Could not read theme.conf: {e}"

    parser = configparser.ConfigParser(strict=False, interpolation=None)
    try:
        parser.read_string(content, source=str(p))
    except configparser.MissingSectionHeaderError as mshe:
        return False, f"theme.conf has missing section header at line {mshe.lineno}: {mshe.args[2] if len(mshe.args) > 2 else mshe}"
    except configparser.ParsingError as pe:
        # pe.errors is a list of (lineno, line)
        line_info = ", ".join(f"line {lineno}" for lineno, _ in getattr(pe, "errors", []))
        return False, f"theme.conf has invalid INI syntax at {line_info or 'unknown line'}: {pe}"
    except Exception as e:
        return False, f"Failed to parse theme.conf: {e}"

    return True, "theme.conf is valid."


class ArchiveInstallerWorkerSignals(QObject):
    finished = Signal(bool, object, str)  # (success, path, message)
    progress = Signal(str)


class ArchiveInstallerRunnable(QRunnable):
    """Background runnable for extracting large archives (>10MB) without blocking GUI."""

    def __init__(self, archive_path: Path, target_dir: Path, is_replace: bool = False):
        super().__init__()
        self.archive_path = archive_path
        self.target_dir = target_dir
        self.is_replace = is_replace
        self.signals = ArchiveInstallerWorkerSignals()

    def run(self):
        ok, dest_path, msg = ArchiveInstaller.perform_extraction(
            self.archive_path,
            self.target_dir,
            is_replace=self.is_replace,
            progress_callback=self.signals.progress.emit,
        )
        self.signals.finished.emit(ok, dest_path, msg)


class ArchiveInstaller:
    """Manages theme archive extraction with validation and backup on conflict."""

    @classmethod
    def install(
        cls,
        archive_path: Path | str,
        dest_base: Optional[Path | str] = None,
        parent_widget: Optional[QWidget] = None,
        on_completed: Optional[Callable[[bool, Optional[Path], str], None]] = None,
    ) -> Tuple[bool, Optional[Path], str]:
        """
        Main installation entry point.
        Checks conflicts, prompts user for replacement, and executes installation.
        If file > 10MB and on_completed callback is provided, runs asynchronously via QThreadPool.
        """
        arch = Path(archive_path).resolve()
        if not arch.exists() or not arch.is_file():
            msg = f"Archive file does not exist: {arch}"
            if parent_widget:
                QMessageBox.critical(parent_widget, "File Not Found", msg)
            return False, None, msg

        derived_name = derive_theme_name(arch)
        base = Path(dest_base) if dest_base else SYSTEM_THEMES_DIR
        target_dest = base / derived_name

        # Conflict check: if target dir already exists
        is_replace = False
        if target_dest.exists():
            if parent_widget:
                reply = QMessageBox.question(
                    parent_widget,
                    "Theme Already Exists",
                    f"Theme '{derived_name}' already exists in {base}.\n\nDo you want to replace it?\n"
                    f"(An automatic backup will be created)",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Cancel,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return False, None, f"Installation of '{derived_name}' cancelled by user."
                is_replace = True
            else:
                is_replace = True

        # Check file size for async execution
        size_bytes = arch.stat().st_size
        is_large = size_bytes > 10 * 1024 * 1024  # > 10 MB

        if is_large and on_completed is not None:
            runnable = ArchiveInstallerRunnable(arch, target_dest, is_replace=is_replace)
            runnable.signals.finished.connect(on_completed)
            QThreadPool.globalInstance().start(runnable)
            return True, target_dest, "Extraction started in background."

        # Synchronous execution
        ok, path, msg = cls.perform_extraction(arch, target_dest, is_replace=is_replace)
        if not ok and parent_widget:
            QMessageBox.critical(parent_widget, "Installation Failed", msg)
        return ok, path, msg

    @classmethod
    def perform_extraction(
        cls,
        arch: Path,
        target_dest: Path,
        is_replace: bool = False,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[bool, Optional[Path], str]:
        """Performs temp extraction, single-folder flattening, validation, backup, and copy."""
        derived_name = target_dest.name
        is_system = str(target_dest).startswith("/usr")

        # 1. If replacing, create backup first
        if target_dest.exists() and is_replace:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = target_dest.parent / f"{derived_name}.bak.{timestamp}"
            if progress_callback:
                progress_callback(f"Backing up existing theme to {backup_path.name}...")

            if is_system:
                mv_bin = shutil.which("mv") or "/usr/bin/mv"
                rc, out, err = run_command([mv_bin, str(target_dest), str(backup_path)], privileged=True)
                if rc != 0:
                    return False, None, f"Failed to create backup of existing theme: {err or out}"
            else:
                try:
                    shutil.move(str(target_dest), str(backup_path))
                except Exception as e:
                    return False, None, f"Failed to backup existing theme: {e}"

        with tempfile.TemporaryDirectory(prefix="sddm_install_extract_") as temp_dir:
            temp_path = Path(temp_dir)
            if progress_callback:
                progress_callback("Extracting archive...")

            # Extract archive
            try:
                if arch.suffix.lower() == ".zip":
                    with zipfile.ZipFile(arch, "r") as zf:
                        zf.extractall(temp_path)
                else:
                    with tarfile.open(arch, "r:*") as tf:
                        for member in tf.getmembers():
                            t = temp_path / member.name
                            if not t.resolve().is_relative_to(temp_path.resolve()):
                                return False, None, "Archive contains malicious path traversal components."
                        tf.extractall(temp_path)
            except Exception as e:
                return False, None, f"Failed to extract archive: {e}"

            # Single-wrapped-folder check & flattening:
            # if extraction yields exactly one subdirectory containing theme.conf, flatten it
            extracted_items = list(temp_path.iterdir())
            theme_source_dir = temp_path

            if len(extracted_items) == 1 and extracted_items[0].is_dir():
                sub = extracted_items[0]
                if (sub / "theme.conf").exists() or ThemeScanner.is_valid_theme_dir(sub):
                    theme_source_dir = sub
            else:
                # Traverse to locate theme root
                located = ThemeInstaller._locate_theme_root(temp_path)
                if located:
                    theme_source_dir = located

            # Validate theme.conf existence
            conf_file = theme_source_dir / "theme.conf"
            if not conf_file.exists():
                return False, None, "Archive does not contain required 'theme.conf' file."

            # Validate theme.conf syntax with line reporting
            valid_ini, ini_err = validate_theme_conf(conf_file)
            if not valid_ini:
                return False, None, f"Invalid theme.conf: {ini_err}"

            # Normalize permissions inside temp dir
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

            # Ensure preview image exists
            ThemeInstaller._ensure_preview_exists(theme_source_dir)

            # Move/copy to destination
            if is_system:
                if target_dest.exists():
                    remove_path_privileged(target_dest)

                cp_ok, cp_msg = copy_directory_privileged(theme_source_dir, target_dest)
                if not cp_ok:
                    return False, None, f"Failed to install theme to {target_dest}: {cp_msg}"

                # Purge any lingering user copy to prevent conflicts
                user_copy = USER_THEMES_DIR / derived_name
                if user_copy.exists():
                    shutil.rmtree(user_copy, ignore_errors=True)
            else:
                if target_dest.exists():
                    shutil.rmtree(target_dest, ignore_errors=True)
                try:
                    shutil.copytree(theme_source_dir, target_dest)
                except Exception as e:
                    return False, None, f"Failed to copy theme to {target_dest}: {e}"

            # Verify final destination has theme files
            if not ThemeScanner.is_valid_theme_dir(target_dest):
                if is_system:
                    remove_path_privileged(target_dest)
                else:
                    shutil.rmtree(target_dest, ignore_errors=True)
                return False, None, "Extracted files do not form a valid SDDM theme."

            return True, target_dest, f"Theme '{derived_name}' installed successfully."
