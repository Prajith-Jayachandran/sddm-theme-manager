"""
SDDM Theme Manager - Live Greeter Runner & Error Parser
Provides asynchronous execution of SDDM greeter test mode with real-time stdout/stderr
streaming, pre-flight static verification, process supervision, and smart QML error diagnosis.
"""

import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, QProcess, Signal


class QMLErrorParser:
    """
    Parses SDDM and Qt/QML runtime logs to extract file paths, line numbers,
    error messages, and actionable quick-fix suggestions for theme creators.
    """

    # Matches lines like:
    # file:///usr/share/sddm/themes/test/Main.qml:42:15: Cannot assign to non-existent property "foo"
    # /tmp/test/Main.qml:12: ReferenceError: bar is not defined
    # Main.qml:10:5: Syntax error
    QML_FILE_LINE_RE = re.compile(
        r"(?:file://)?([a-zA-Z0-9_\-\.\/]+\.qml):(\d+)(?::(\d+))?:?\s*(.*)",
        re.IGNORECASE,
    )

    # Known recurring SDDM failure signatures & remediation hints
    KNOWN_SIGNATURES = [
        (
            re.compile(r"Library import requires a version", re.IGNORECASE),
            "Qt 5 runtime requires explicit import versions. Replace versionless imports with 'import QtQuick 2.15', 'import QtQuick.Window 2.15', etc.",
        ),
        (
            re.compile(r"module \"([^\"]+)\" is not installed", re.IGNORECASE),
            "The QML module '{0}' is not installed in the system Qt runtime. Check if you need to install package 'qt6-5compat', 'qt5-quickcontrols', or equivalent.",
        ),
        (
            re.compile(r"Cannot assign to non-existent property \"background\"", re.IGNORECASE),
            "SddmComponents 2.0 'Button' lacks a 'background' property (which shadows QtQuick.Controls). Use a custom styled Rectangle with a MouseArea instead.",
        ),
        (
            re.compile(r"Implicitly defined onFoo properties in Connections are deprecated", re.IGNORECASE),
            "Update Connection handlers to Qt 5.15+ / Qt 6 syntax: use 'function onLoginFailed() { ... }' instead of 'onLoginFailed: { ... }'.",
        ),
        (
            re.compile(r"Qt5Compat\.GraphicalEffects.*is not installed", re.IGNORECASE),
            "Qt5Compat is Qt 6-only. On Qt 5 systems, install and use 'import QtGraphicalEffects 1.15' or avoid shader masks with native 'clip: true'.",
        ),
        (
            re.compile(r"Cannot open:.*No such file or directory", re.IGNORECASE),
            "Asset or component file could not be found. Check relative file paths, capitalization, and metadata.desktop entries.",
        ),
        (
            re.compile(r"ReferenceError:\s*(\w+)\s*is not defined", re.IGNORECASE),
            "Identifier '{0}' is referenced before declaration or does not exist in the active QML scope.",
        ),
        (
            re.compile(r"Syntax error", re.IGNORECASE),
            "QML syntax error detected. Check matching braces {}, brackets [], semicolons, and string quote closures.",
        ),
    ]

    @classmethod
    def parse_line(cls, line: str) -> Dict[str, any]:
        """
        Parses a single log line and returns diagnostic dictionary.
        Returns:
            {
                "file": Optional[str],
                "line": Optional[int],
                "col": Optional[int],
                "message": str,
                "suggestion": Optional[str],
                "is_error": bool,
                "is_warning": bool
            }
        """
        stripped = line.strip()
        result = {
            "file": None,
            "line": None,
            "col": None,
            "message": stripped,
            "suggestion": None,
            "is_error": False,
            "is_warning": False,
        }

        # Check error vs warning flags
        lower = stripped.lower()
        if any(k in lower for k in ["error", "cannot", "failed", "typeerror", "referenceerror", "syntax error"]):
            result["is_error"] = True
        elif any(k in lower for k in ["warning", "deprecated", "fallback"]):
            result["is_warning"] = True

        # Extract file and line number
        match = cls.QML_FILE_LINE_RE.search(stripped)
        if match:
            file_match = match.group(1)
            result["file"] = Path(file_match).name
            result["full_path"] = file_match
            try:
                result["line"] = int(match.group(2))
            except (ValueError, TypeError):
                result["line"] = None

            if match.group(3):
                try:
                    result["col"] = int(match.group(3))
                except (ValueError, TypeError):
                    result["col"] = None

            msg_tail = match.group(4).strip() if match.group(4) else ""
            if msg_tail:
                result["message"] = msg_tail

        # Generate intelligent suggestions based on known patterns
        for pattern, suggestion_template in cls.KNOWN_SIGNATURES:
            sig_match = pattern.search(stripped)
            if sig_match:
                if "{0}" in suggestion_template and sig_match.groups():
                    result["suggestion"] = suggestion_template.format(sig_match.group(1))
                else:
                    result["suggestion"] = suggestion_template
                break

        return result


class LiveGreeterRunner(QObject):
    """
    Subprocess manager for live SDDM greeter testing.
    Runs sddm-greeter-qt6 (or sddm-greeter) in test mode, captures stdout/stderr,
    tracks status, and supports graceful hot-reloading.
    """

    # Signals
    started = Signal(int)  # pid
    output_received = Signal(str, str, dict)  # (raw_text, level: "info"|"warn"|"error"|"preflight", diagnostic_dict)
    finished = Signal(int, str)  # (exit_code, exit_status_str)
    preflight_failed = Signal(str, int)  # (error_message, line_number)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._process: Optional[QProcess] = None
        self._current_theme_path: Optional[Path] = None
        self._pid: int = 0

    @property
    def pid(self) -> int:
        return self._pid

    def is_running(self) -> bool:
        return self._process is not None and self._process.state() != QProcess.NotRunning

    @staticmethod
    def preflight_check(
        theme_path: Path,
        active_file_path: Optional[Path] = None,
        text_content: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Static pre-flight inspection before launching the greeter.
        Checks brace/bracket/parentheses integrity and entrypoint validity.
        Returns:
            (is_valid: bool, error_message: Optional[str], line_number: Optional[int])
        """
        if not theme_path.exists():
            return False, f"Theme directory does not exist: {theme_path}", None

        # Check metadata.desktop entrypoint
        metadata_file = theme_path / "metadata.desktop"
        main_script = "Main.qml"
        if metadata_file.exists():
            try:
                for line in metadata_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if line.strip().startswith("MainScript="):
                        main_script = line.split("=", 1)[1].strip()
                        break
            except Exception:
                pass

        main_qml = theme_path / main_script
        if not main_qml.exists() and not (theme_path / "Main.qml").exists():
            return False, f"Greeter entry point '{main_script}' not found in theme directory.", 1

        # If inspecting active QML file content
        content_to_check = text_content
        target_path = active_file_path or main_qml
        if content_to_check is None and target_path.exists() and target_path.suffix.lower() == ".qml":
            try:
                content_to_check = target_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                content_to_check = None

        if content_to_check is not None and (target_path.suffix.lower() == ".qml"):
            # 1. Balanced braces, brackets, and parentheses check with line tracking
            stack = []
            pairs = {')': '(', '}': '{', ']': '['}
            lines = content_to_check.splitlines()

            in_multiline_comment = False
            for line_idx, line_str in enumerate(lines, start=1):
                i = 0
                while i < len(line_str):
                    if in_multiline_comment:
                        if line_str[i:i+2] == "*/":
                            in_multiline_comment = False
                            i += 2
                        else:
                            i += 1
                        continue

                    # Single line comments
                    if line_str[i:i+2] == "//":
                        break
                    # Start of multiline comments
                    if line_str[i:i+2] == "/*":
                        in_multiline_comment = True
                        i += 2
                        continue

                    char = line_str[i]
                    if char in "({[":
                        stack.append((char, line_idx))
                    elif char in ")}]":
                        expected = pairs[char]
                        if not stack:
                            return False, f"Unmatched closing '{char}' with no opening '{expected}'", line_idx
                        top_char, top_line = stack.pop()
                        if top_char != expected:
                            return False, f"Mismatched closing '{char}'. Expected closing for '{top_char}' opened at line {top_line}", line_idx
                    i += 1

            if stack:
                top_char, top_line = stack[-1]
                return False, f"Unclosed opening '{top_char}' from line {top_line}", top_line

        return True, None, None

    def start(
        self,
        theme_path: Path,
        active_file_path: Optional[Path] = None,
        text_content: Optional[str] = None,
    ) -> bool:
        """
        Executes pre-flight checks and spawns the live greeter subprocess.
        """
        self._current_theme_path = theme_path

        # 1. Pre-flight static validation
        valid, err_msg, err_line = self.preflight_check(theme_path, active_file_path, text_content)
        if not valid:
            diag = {
                "file": active_file_path.name if active_file_path else "Main.qml",
                "line": err_line or 1,
                "col": None,
                "message": err_msg,
                "suggestion": "Fix syntax balance before running live greeter.",
                "is_error": True,
                "is_warning": False,
            }
            self.output_received.emit(f"Pre-flight error: {err_msg}", "preflight", diag)
            self.preflight_failed.emit(err_msg, err_line or 1)
            return False

        # 2. Stop any existing instance
        if self.is_running():
            self.stop()

        # 3. Detect greeter binary
        greeter_bin = None
        if os.path.exists("/usr/bin/sddm-greeter-qt6"):
            greeter_bin = "/usr/bin/sddm-greeter-qt6"
        elif os.path.exists("/usr/bin/sddm-greeter"):
            greeter_bin = "/usr/bin/sddm-greeter"
        else:
            found = shutil.which("sddm-greeter-qt6") or shutil.which("sddm-greeter")
            if found:
                greeter_bin = found

        if not greeter_bin:
            diag = {
                "file": None,
                "line": None,
                "col": None,
                "message": "Neither sddm-greeter-qt6 nor sddm-greeter found on system.",
                "suggestion": "Ensure SDDM is installed on your Linux system.",
                "is_error": True,
                "is_warning": False,
            }
            self.output_received.emit("Execution error: Greeter binary not found.", "error", diag)
            return False

        # 4. Spawn QProcess
        self._process = QProcess(self)
        self._process.setProgram(greeter_bin)
        self._process.setArguments(["--test-mode", "--theme", str(theme_path)])

        self._process.readyReadStandardError.connect(self._on_ready_read_stderr)
        self._process.readyReadStandardOutput.connect(self._on_ready_read_stdout)
        self._process.started.connect(self._on_started)
        self._process.finished.connect(self._on_finished)

        self.output_received.emit(
            f"Pre-flight OK. Spawning: {greeter_bin} --test-mode --theme {theme_path.name}",
            "info",
            {"file": None, "line": None, "col": None, "message": "Pre-flight checks passed.", "suggestion": None, "is_error": False, "is_warning": False},
        )

        self._process.start()
        return True

    def stop(self):
        """Terminates running greeter process."""
        if not self._process:
            return

        if self._process.state() != QProcess.NotRunning:
            self._process.terminate()
            if not self._process.waitForFinished(1000):
                self._process.kill()
                self._process.waitForFinished(500)

        self._pid = 0
        self._process = None

    def _on_started(self):
        if self._process:
            self._pid = self._process.processId()
            self.started.emit(self._pid)
            diag = {"file": None, "line": None, "col": None, "message": f"Greeter active with PID {self._pid}", "suggestion": None, "is_error": False, "is_warning": False}
            self.output_received.emit(f"Greeter process active (PID: {self._pid})", "info", diag)

    def _on_ready_read_stderr(self):
        if not self._process:
            return
        data = self._process.readAllStandardError().data().decode("utf-8", errors="replace")
        for line in data.splitlines():
            line_str = line.strip()
            if not line_str:
                continue
            diag = QMLErrorParser.parse_line(line_str)
            level = "error" if diag["is_error"] else ("warn" if diag["is_warning"] else "info")
            self.output_received.emit(line_str, level, diag)

    def _on_ready_read_stdout(self):
        if not self._process:
            return
        data = self._process.readAllStandardOutput().data().decode("utf-8", errors="replace")
        for line in data.splitlines():
            line_str = line.strip()
            if not line_str:
                continue
            diag = QMLErrorParser.parse_line(line_str)
            level = "info"
            self.output_received.emit(line_str, level, diag)

    def _on_finished(self, exit_code: int, exit_status):
        status_str = "Normal" if exit_status == QProcess.NormalExit else "Crashed"
        self._pid = 0
        self.finished.emit(exit_code, status_str)
        level = "info" if exit_code == 0 or exit_code == 124 else "warn"
        diag = {"file": None, "line": None, "col": None, "message": f"Greeter finished: {status_str} (code: {exit_code})", "suggestion": None, "is_error": (exit_code != 0 and exit_code != 124), "is_warning": False}
        self.output_received.emit(f"Greeter process stopped ({status_str}, exit code: {exit_code})", level, diag)
