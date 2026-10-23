"""
SDDM Theme Manager - Qt5 vs Qt6 Compatibility Linter Dialog
Presents validation results and provides 1-click auto-patching for older themes.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.linter import ThemeLinter
from core.theme_scanner import Theme


class LinterDialog(QDialog):
    """Dialog displaying theme compatibility diagnostics and auto-fix controls."""

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setWindowTitle(f"Compatibility Diagnostics — {theme.name}")
        self.setMinimumSize(540, 460)
        self.report = ThemeLinter.lint_theme(self.theme.path)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(18, 18, 18, 18)

        # Header with status badge
        header_layout = QHBoxLayout()
        header_title = QLabel(f"Compatibility Report: {self.theme.name}")
        header_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #7aa2f7;")
        header_layout.addWidget(header_title)

        status_badge = QLabel()
        if self.report.has_errors:
            status_badge.setText("⚠️ ISSUES DETECTED")
            status_badge.setStyleSheet("background-color: #f7768e; color: #ffffff; font-weight: bold; padding: 4px 8px; border-radius: 4px;")
        else:
            status_badge.setText("✓ QT 6 READY")
            status_badge.setStyleSheet("background-color: #9ece6a; color: #1a1b26; font-weight: bold; padding: 4px 8px; border-radius: 4px;")
        header_layout.addWidget(status_badge)
        layout.addLayout(header_layout)

        # Missing packages warning banner if applicable
        if self.report.missing_packages:
            pkg_frame = QFrame()
            pkg_frame.setStyleSheet("background-color: #2e2839; border-left: 4px solid #e0af68; padding: 8px;")
            pkg_layout = QVBoxLayout(pkg_frame)
            pkg_lbl = QLabel(f"Missing System Package(s):\n• " + "\n• ".join(self.report.missing_packages))
            pkg_lbl.setStyleSheet("color: #e0af68; font-size: 12px;")
            pkg_layout.addWidget(pkg_lbl)
            layout.addWidget(pkg_frame)

        # Scroll Area for issues
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: #1a1b26; border-radius: 6px;")

        issues_widget = QWidget()
        issues_layout = QVBoxLayout(issues_widget)
        issues_layout.setSpacing(10)
        issues_layout.setContentsMargins(10, 10, 10, 10)

        if not self.report.issues:
            no_issue_lbl = QLabel("No compatibility issues detected. Theme should load cleanly on modern greeters.")
            no_issue_lbl.setStyleSheet("color: #9ece6a; padding: 20px;")
            no_issue_lbl.setAlignment(Qt.AlignCenter)
            issues_layout.addWidget(no_issue_lbl)
        else:
            for issue in self.report.issues:
                card = QFrame()
                card.setStyleSheet("background-color: #24283b; border-radius: 4px; padding: 8px;")
                card_layout = QVBoxLayout(card)
                card_layout.setSpacing(4)

                top_row = QHBoxLayout()
                sev_lbl = QLabel(issue.severity)
                if issue.severity == "ERROR":
                    sev_lbl.setStyleSheet("color: #f7768e; font-weight: bold; font-size: 11px;")
                elif issue.severity == "WARNING":
                    sev_lbl.setStyleSheet("color: #e0af68; font-weight: bold; font-size: 11px;")
                else:
                    sev_lbl.setStyleSheet("color: #7aa2f7; font-weight: bold; font-size: 11px;")

                file_lbl = QLabel(f"{issue.file_path.name}:{issue.line_number}")
                file_lbl.setStyleSheet("color: #787c99; font-size: 11px;")

                top_row.addWidget(sev_lbl)
                top_row.addWidget(file_lbl)
                top_row.addStretch()
                card_layout.addLayout(top_row)

                msg_lbl = QLabel(issue.message)
                msg_lbl.setWordWrap(True)
                msg_lbl.setStyleSheet("color: #c0caf5; font-size: 12px;")
                card_layout.addWidget(msg_lbl)

                if issue.suggested_fix:
                    fix_lbl = QLabel(f"Suggested fix: {issue.suggested_fix}")
                    fix_lbl.setStyleSheet("color: #73daca; font-size: 11px; font-style: italic;")
                    card_layout.addWidget(fix_lbl)

                issues_layout.addWidget(card)

        issues_layout.addStretch()
        scroll.setWidget(issues_widget)
        layout.addWidget(scroll, 1)

        # Action Buttons
        btn_layout = QHBoxLayout()

        if self.report.has_errors:
            self.btn_patch = QPushButton("🛡️ Auto-Patch for Qt 6")
            self.btn_patch.setStyleSheet("background-color: #e0af68; color: #1a1b26; font-weight: bold; padding: 6px 14px;")
            self.btn_patch.clicked.connect(self._run_auto_patch)
            btn_layout.addWidget(self.btn_patch)

        btn_layout.addStretch()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

    def _run_auto_patch(self):
        ok, msg, count = ThemeLinter.patch_theme_for_qt6(self.theme.path)
        if ok:
            QMessageBox.information(
                self,
                "Patch Complete",
                f"{msg}\n\nOriginal files have been backed up as *.qml.bak.",
            )
            self.accept()
        else:
            QMessageBox.critical(self, "Patch Failed", msg)
