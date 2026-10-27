"""
SDDM Theme Manager - Live Preview Runner
Manages launching and terminating sddm-greeter in --test-mode.
"""

import os
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple

from PySide6.QtCore import QObject, QThread, Signal

from .polkit import PolkitConfig, detect_sddm_qt_version


class PreviewProcessWatcher(QThread):
    """Monitors the running greeter process and emits finished signal when it exits."""

    finished_signal = Signal(int, str)  # returncode, error message

    def __init__(self, process: subprocess.Popen):
        super().__init__()
        self.process = process

    def run(self):
        try:
            _, stderr_data = self.process.communicate()
            rc = self.process.returncode
            self.finished_signal.emit(rc, stderr_data or "")
        except Exception as e:
            self.finished_signal.emit(-1, str(e))


class PreviewManager(QObject):
    """Manages launching, tracking, and stopping the SDDM greeter test window."""

    preview_started = Signal(str)  # theme path
    preview_stopped = Signal(int, str)  # return code, message
    preview_error = Signal(str)  # error description

    def __init__(self):
        super().__init__()
        self.current_process: Optional[subprocess.Popen] = None
        self.current_theme_path: Optional[Path] = None
        self.watcher_thread: Optional[PreviewProcessWatcher] = None

    def is_running(self) -> bool:
        """Returns True if a preview greeter process is actively running."""
        if self.current_process is not None:
            return self.current_process.poll() is None
        return False

    def get_greeter_binary(self, theme_qt_version: str = "6") -> Optional[str]:
        """
        Determines the appropriate greeter binary.
        Prefers sddm-greeter-qt6 unless theme is explicitly Qt5 or only sddm-greeter exists.
        """
        qt6_bin = shutil.which("sddm-greeter-qt6")
        qt5_bin = shutil.which("sddm-greeter")

        if theme_qt_version == "5" and qt5_bin:
            return qt5_bin
        if qt6_bin:
            return qt6_bin
        if qt5_bin:
            return qt5_bin
        return None

    def start_preview(self, theme_path: Path | str, qt_version: str = "6") -> Tuple[bool, str]:
        """
        Launches sddm-greeter --test-mode --theme <theme_path>.
        Terminates any previously running preview process first.
        """
        t_path = Path(theme_path).resolve()
        if not t_path.exists():
            msg = f"Theme path does not exist: {t_path}"
            self.preview_error.emit(msg)
            return False, msg

        # Stop existing preview if running
        if self.is_running():
            self.stop_preview()

        greeter_bin = self.get_greeter_binary(qt_version)
        if not greeter_bin:
            msg = "Neither sddm-greeter-qt6 nor sddm-greeter was found on the system."
            self.preview_error.emit(msg)
            return False, msg

        # Validate that the theme has its MainScript before launching greeter
        main_script = "Main.qml"
        metadata_file = t_path / "metadata.desktop"
        if metadata_file.exists():
            try:
                for line in metadata_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if line.strip().startswith("MainScript="):
                        main_script = line.split("=", 1)[1].strip()
                        break
            except Exception:
                pass

        script_path = t_path / main_script
        if not script_path.exists():
            msg = f"Cannot preview theme '{t_path.name}': Main script '{main_script}' was not found in directory."
            self.preview_error.emit(msg)
            return False, msg

        cmd = [
            greeter_bin,
            "--test-mode",
            "--theme",
            str(t_path),
            "--qwindowtitle",
            f"SDDM Preview: {t_path.name} (Press Alt+F4 to Close)",
        ]

        if PolkitConfig.debug:
            print(f"[DEBUG] Launching preview: {' '.join(cmd)}")

        # Inherit current graphical session environment and allow local XHR reads
        env = os.environ.copy()
        env["QML_XHR_ALLOW_FILE_READ"] = "1"

        try:
            self.current_process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.current_theme_path = t_path

            # Start thread to wait for process exit without blocking UI
            self.watcher_thread = PreviewProcessWatcher(self.current_process)
            self.watcher_thread.finished_signal.connect(self._on_process_finished)
            self.watcher_thread.start()

            self.preview_started.emit(str(t_path))
            return True, "Preview started."
        except Exception as e:
            msg = f"Failed to launch greeter preview: {e}"
            self.preview_error.emit(msg)
            return False, msg

    def stop_preview(self):
        """Terminates the active preview process gracefully, then kills if necessary."""
        if self.current_process is not None and self.current_process.poll() is None:
            try:
                self.current_process.terminate()
                try:
                    self.current_process.wait(timeout=1.5)
                except subprocess.TimeoutExpired:
                    self.current_process.kill()
                    self.current_process.wait(timeout=1.0)
            except Exception:
                pass

        self.current_process = None
        self.current_theme_path = None

    def _on_process_finished(self, returncode: int, stderr_msg: str):
        """Internal callback when greeter process terminates."""
        self.current_process = None
        self.current_theme_path = None
        self.preview_stopped.emit(returncode, stderr_msg)
