"""
SDDM Theme Manager - Live Diagnostics Console Drawer
Docked terminal console for real-time stderr/stdout streaming, colorized error logs,
clickable line navigation, quick-fix suggestions, and process status indicators.
"""

from datetime import datetime
from typing import Dict, Optional

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QColor, QFont, QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class LiveConsoleDrawer(QWidget):
    """
    Collapsible console drawer for real-time live greeter feedback.
    Emits jump_requested(filename, line_number) when creators click error lines.
    """

    jump_requested = Signal(str, int)  # filename, line_number

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._is_collapsed = False
        self._error_count = 0
        self._warning_count = 0
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Header Toolbar
        self.header_frame = QFrame(self)
        self.header_frame.setStyleSheet(
            "QFrame {"
            "  background-color: #1a1b26;"
            "  border-top: 1px solid #3b4261;"
            "  border-bottom: 1px solid #24283b;"
            "  padding: 2px 6px;"
            "}"
        )
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(6, 4, 6, 4)
        header_layout.setSpacing(10)

        lbl_title = QLabel("<b>🛠️ Live Diagnostics Console</b>", self.header_frame)
        lbl_title.setStyleSheet("QLabel { color: #c0caf5; font-size: 12px; }")
        header_layout.addWidget(lbl_title)

        # Status badge
        self.lbl_status = QLabel("● IDLE", self.header_frame)
        self.lbl_status.setStyleSheet(
            "QLabel {"
            "  background-color: #24283b;"
            "  color: #7aa2f7;"
            "  font-size: 11px;"
            "  font-weight: bold;"
            "  padding: 2px 8px;"
            "  border-radius: 4px;"
            "}"
        )
        header_layout.addWidget(self.lbl_status)

        # Counter badge
        self.lbl_counts = QLabel("0 Errors | 0 Warnings", self.header_frame)
        self.lbl_counts.setStyleSheet("QLabel { color: #787c99; font-size: 11px; }")
        header_layout.addWidget(self.lbl_counts)

        header_layout.addStretch()

        # Auto-scroll checkbox
        self.chk_autoscroll = QCheckBox("Auto-Scroll", self.header_frame)
        self.chk_autoscroll.setChecked(True)
        self.chk_autoscroll.setStyleSheet("QCheckBox { color: #9aa5ce; font-size: 11px; }")
        header_layout.addWidget(self.chk_autoscroll)

        # Clear button
        self.btn_clear = QToolButton(self.header_frame)
        self.btn_clear.setText("🗑️ Clear")
        self.btn_clear.setToolTip("Clear console output")
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.setStyleSheet(
            "QToolButton {"
            "  background: #24283b; color: #c0caf5; border: 1px solid #3b4261;"
            "  border-radius: 4px; padding: 2px 8px; font-size: 11px;"
            "}"
            "QToolButton:hover { background: #2f354d; }"
        )
        self.btn_clear.clicked.connect(self.clear_console)
        header_layout.addWidget(self.btn_clear)

        # Collapse / Expand button
        self.btn_toggle = QToolButton(self.header_frame)
        self.btn_toggle.setText("▲ Hide")
        self.btn_toggle.setToolTip("Toggle diagnostics console visibility")
        self.btn_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_toggle.setStyleSheet(
            "QToolButton {"
            "  background: #24283b; color: #c0caf5; border: 1px solid #3b4261;"
            "  border-radius: 4px; padding: 2px 8px; font-size: 11px;"
            "}"
            "QToolButton:hover { background: #2f354d; }"
        )
        self.btn_toggle.clicked.connect(self.toggle_collapsed)
        header_layout.addWidget(self.btn_toggle)

        main_layout.addWidget(self.header_frame)

        # 2. Rich Text Browser for Terminal Output
        self.text_browser = QTextBrowser(self)
        self.text_browser.setOpenLinks(False)
        self.text_browser.anchorClicked.connect(self._on_anchor_clicked)
        self.text_browser.setStyleSheet(
            "QTextBrowser {"
            "  background-color: #0d0f18;"
            "  color: #c0caf5;"
            "  border: none;"
            "  font-family: 'JetBrains Mono', 'Fira Code', 'DejaVu Sans Mono', monospace;"
            "  font-size: 11px;"
            "  padding: 6px 8px;"
            "}"
        )
        self.text_browser.setMinimumHeight(80)
        main_layout.addWidget(self.text_browser, 1)

    def is_collapsed(self) -> bool:
        return self._is_collapsed

    def toggle_collapsed(self):
        self.set_collapsed(not self._is_collapsed)

    def set_collapsed(self, collapsed: bool):
        self._is_collapsed = collapsed
        self.text_browser.setVisible(not collapsed)
        if collapsed:
            self.btn_toggle.setText("▼ Show")
            self.setMaximumHeight(self.header_frame.sizeHint().height() + 6)
        else:
            self.btn_toggle.setText("▲ Hide")
            self.setMaximumHeight(16777215)
            self.setMinimumHeight(120)

    def set_status(self, text: str, state: str = "idle"):
        """
        Updates status badge:
        state: 'idle', 'running', 'error', 'warn', 'preflight'
        """
        color_map = {
            "idle": ("#24283b", "#7aa2f7"),
            "running": ("#143a29", "#73daca"),
            "error": ("#3c1626", "#f7768e"),
            "warn": ("#362c19", "#e0af68"),
            "preflight": ("#162a3c", "#7dcfff"),
        }
        bg, fg = color_map.get(state, ("#24283b", "#7aa2f7"))
        self.lbl_status.setText(f"● {text.upper()}")
        self.lbl_status.setStyleSheet(
            f"QLabel {{"
            f"  background-color: {bg};"
            f"  color: {fg};"
            f"  font-size: 11px;"
            f"  font-weight: bold;"
            f"  padding: 2px 8px;"
            f"  border-radius: 4px;"
            f"}}"
        )

    def _update_counts(self):
        self.lbl_counts.setText(f"{self._error_count} Errors | {self._warning_count} Warnings")
        if self._error_count > 0:
            self.lbl_counts.setStyleSheet("QLabel { color: #f7768e; font-size: 11px; font-weight: bold; }")
        elif self._warning_count > 0:
            self.lbl_counts.setStyleSheet("QLabel { color: #e0af68; font-size: 11px; }")
        else:
            self.lbl_counts.setStyleSheet("QLabel { color: #787c99; font-size: 11px; }")

    def clear_console(self):
        self.text_browser.clear()
        self._error_count = 0
        self._warning_count = 0
        self._update_counts()

    def log(self, message: str, level: str = "info", diag: Optional[Dict[str, any]] = None):
        """
        Appends colorized diagnostic message with clickable error links and actionable suggestions.
        """
        time_str = datetime.now().strftime("%H:%M:%S")

        # Track counts
        if level == "error" or (diag and diag.get("is_error")):
            self._error_count += 1
        elif level == "warn" or (diag and diag.get("is_warning")):
            self._warning_count += 1
        self._update_counts()

        # Badge colors
        level_styles = {
            "info": ("#7aa2f7", "INFO"),
            "warn": ("#e0af68", "WARN"),
            "error": ("#f7768e", "ERROR"),
            "preflight": ("#7dcfff", "PRE-FLIGHT"),
        }
        color, label = level_styles.get(level, ("#c0caf5", level.upper()))

        # Build HTML entry
        html = f"<div style='margin-bottom: 3px; line-height: 1.4;'>"
        html += f"<span style='color: #565f89;'>[{time_str}]</span> "
        html += f"<span style='color: {color}; font-weight: bold;'>[{label}]</span> "
        html += f"<span style='color: #c0caf5;'>{self._escape_html(message)}</span>"

        # Clickable jump link if file and line were parsed
        if diag and diag.get("file") and diag.get("line"):
            file_name = diag["file"]
            line_no = diag["line"]
            col_no = f":{diag['col']}" if diag.get("col") else ""
            html += f" <a href='jump:{file_name}:{line_no}' style='color: #2ac3de; text-decoration: underline; font-weight: bold;'>👉 [⚡ Jump to {file_name}:{line_no}{col_no}]</a>"

        # Quick-fix suggestion callout box
        if diag and diag.get("suggestion"):
            html += (
                f"<div style='margin: 3px 0 4px 18px; padding: 4px 8px; "
                f"background-color: #1b1e2e; border-left: 3px solid #e0af68; border-radius: 2px; "
                f"color: #e0af68; font-size: 11px;'>"
                f"💡 <b>Suggestion:</b> {self._escape_html(diag['suggestion'])}"
                f"</div>"
            )

        html += "</div>"

        # Append HTML
        self.text_browser.append(html)

        if self.chk_autoscroll.isChecked():
            cursor = self.text_browser.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.text_browser.setTextCursor(cursor)

    def _on_anchor_clicked(self, url: QUrl):
        url_str = url.toString()
        if url_str.startswith("jump:"):
            parts = url_str[len("jump:"):].split(":")
            if len(parts) >= 2:
                filename = parts[0]
                try:
                    line_no = int(parts[1])
                    self.jump_requested.emit(filename, line_no)
                except ValueError:
                    pass

    @staticmethod
    def _escape_html(text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )
