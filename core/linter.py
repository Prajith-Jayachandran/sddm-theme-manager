"""
SDDM Theme Manager - Qt5 vs Qt6 Compatibility Linter & Auto-Patcher
Scans theme QML files for deprecated modules, incompatibility pitfalls (such as
QtGraphicalEffects under Qt6), and automatically patches them to prevent black screens.
"""

import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from .polkit import write_file_privileged


@dataclass
class LintIssue:
    file_path: Path
    line_number: int
    severity: str  # "ERROR", "WARNING", "INFO"
    message: str
    suggested_fix: Optional[str] = None


@dataclass
class LintReport:
    theme_name: str
    theme_path: Path
    is_compatible_qt6: bool
    is_compatible_qt5: bool
    issues: List[LintIssue] = field(default_factory=list)
    missing_packages: List[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "ERROR" for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "ERROR")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "WARNING")


class ThemeLinter:
    """Validates and patches SDDM themes for greeter compatibility."""

    @classmethod
    def check_system_qt_packages(cls) -> List[str]:
        """Checks for common Qt runtime libraries needed by SDDM themes."""
        missing = []
        if shutil.which("pacman"):
            # Check pacman database for qt6-5compat
            try:
                import subprocess
                res = subprocess.run(["pacman", "-Qq", "qt6-5compat"], capture_output=True)
                if res.returncode != 0:
                    missing.append("qt6-5compat (needed for legacy graphical effects in Qt 6)")
            except Exception:
                pass
        return missing

    @classmethod
    def lint_theme(cls, theme_dir: Path | str) -> LintReport:
        """
        Thoroughly checks all QML and config files in the theme directory.
        """
        p = Path(theme_dir).resolve()
        issues: List[LintIssue] = []
        requires_qt5_compat = False
        uses_qtquick_controls_1 = False

        if not p.exists():
            return LintReport(p.name, p, False, False, [LintIssue(p, 0, "ERROR", "Theme directory does not exist.")])

        # Scan all .qml files
        qml_files = list(p.rglob("*.qml"))
        if not qml_files:
            issues.append(LintIssue(p, 0, "ERROR", "No QML files found in theme directory."))

        # Check metadata.desktop and MainScript existence
        metadata_file = p / "metadata.desktop"
        if metadata_file.exists():
            main_script = "Main.qml"
            try:
                for line in metadata_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if line.strip().startswith("MainScript="):
                        main_script = line.split("=", 1)[1].strip()
                        break
            except Exception:
                pass

            if not (p / main_script).exists():
                issues.append(LintIssue(
                    file_path=metadata_file,
                    line_number=0,
                    severity="ERROR",
                    message=f"Main script '{main_script}' specified in metadata.desktop does not exist.",
                    suggested_fix=f"Create {main_script} or update MainScript in metadata.desktop.",
                ))
        elif not (p / "Main.qml").exists():
            issues.append(LintIssue(
                file_path=p,
                line_number=0,
                severity="ERROR",
                message="Theme is missing Main.qml entry script.",
                suggested_fix="Create Main.qml as the primary greeter entry point.",
            ))

        for qml in qml_files:
            try:
                lines = qml.read_text(encoding="utf-8", errors="ignore").splitlines()
                for idx, line in enumerate(lines, 1):
                    stripped = line.strip()

                    # 1. Check for legacy QtGraphicalEffects
                    if re.match(r"^import\s+QtGraphicalEffects\b", stripped):
                        requires_qt5_compat = True
                        issues.append(LintIssue(
                            file_path=qml,
                            line_number=idx,
                            severity="ERROR",
                            message="Deprecated 'import QtGraphicalEffects' will crash or cause black screen on Qt 6 greeters.",
                            suggested_fix="Replace with 'import Qt5Compat.GraphicalEffects 6.0'",
                        ))

                    # 2. Check for QtQuick.Controls 1.x
                    if re.match(r"^import\s+QtQuick\.Controls\s+1\.", stripped):
                        uses_qtquick_controls_1 = True
                        issues.append(LintIssue(
                            file_path=qml,
                            line_number=idx,
                            severity="WARNING",
                            message="QtQuick.Controls 1.x is obsolete in Qt 6.",
                            suggested_fix="Upgrade component to QtQuick.Controls 2.x",
                        ))

                    # 3. Check for specific versioned QtQuick imports
                    if re.match(r"^import\s+QtQuick\s+2\.\d+", stripped):
                        issues.append(LintIssue(
                            file_path=qml,
                            line_number=idx,
                            severity="INFO",
                            message="Versioned QtQuick import (QtQuick 2.x) can be simplified in Qt 6.",
                            suggested_fix="Use unversioned 'import QtQuick'",
                        ))

            except Exception as e:
                issues.append(LintIssue(qml, 0, "WARNING", f"Could not read file: {e}"))

        # Determine overall compatibility
        is_qt6_ok = not any(i.severity == "ERROR" for i in issues)
        is_qt5_ok = not uses_qtquick_controls_1

        missing_pkgs = []
        if requires_qt5_compat:
            missing_pkgs = cls.check_system_qt_packages()

        return LintReport(
            theme_name=p.name,
            theme_path=p,
            is_compatible_qt6=is_qt6_ok,
            is_compatible_qt5=is_qt5_ok,
            issues=issues,
            missing_packages=missing_pkgs,
        )

    @classmethod
    def patch_theme_for_qt6(cls, theme_dir: Path | str) -> Tuple[bool, str, int]:
        """
        Auto-patches theme QML files to run safely under Qt6 SDDM greeters.
        Replaces deprecated imports and creates backup files.
        """
        p = Path(theme_dir).resolve()
        is_system = str(p).startswith("/usr")
        patched_count = 0

        qml_files = list(p.rglob("*.qml"))

        # Auto-scaffold Main.qml if theme has no QML files
        main_qml = p / "Main.qml"
        if not main_qml.exists() and not qml_files:
            try:
                from ui.theme_writer import STARTER_MAIN_QML
                if is_system:
                    ok, msg = write_file_privileged(main_qml, STARTER_MAIN_QML)
                    if not ok:
                        return False, f"Failed to generate Main.qml: {msg}", patched_count
                else:
                    main_qml.write_text(STARTER_MAIN_QML, encoding="utf-8")
                patched_count += 1
                qml_files = [main_qml]
            except Exception as e:
                return False, f"Error generating Main.qml: {e}", patched_count
        for qml in qml_files:
            try:
                original = qml.read_text(encoding="utf-8", errors="ignore")
                modified = original

                # 1. Replace QtGraphicalEffects -> Qt5Compat.GraphicalEffects 6.0
                modified = re.sub(
                    r"^import\s+QtGraphicalEffects\b.*$",
                    "import Qt5Compat.GraphicalEffects 6.0",
                    modified,
                    flags=re.MULTILINE,
                )

                # 2. Modernize versioned QtQuick imports
                modified = re.sub(
                    r"^import\s+QtQuick\s+2\.\d+\s*$",
                    "import QtQuick",
                    modified,
                    flags=re.MULTILINE,
                )

                if modified != original:
                    # Create .bak backup if not already present
                    bak_file = qml.with_suffix(".qml.bak")
                    if not bak_file.exists():
                        if is_system:
                            write_file_privileged(bak_file, original)
                        else:
                            bak_file.write_text(original, encoding="utf-8")

                    if is_system:
                        ok, msg = write_file_privileged(qml, modified)
                        if not ok:
                            return False, f"Failed to patch {qml.name}: {msg}", patched_count
                    else:
                        qml.write_text(modified, encoding="utf-8")

                    patched_count += 1

            except Exception as e:
                return False, f"Error processing {qml.name}: {e}", patched_count

        if patched_count > 0:
            return True, f"Successfully patched {patched_count} QML file(s) for Qt 6 compatibility.", patched_count
        return True, "No files needed patching. Theme is already Qt 6 clean.", 0
