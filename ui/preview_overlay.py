"""
SDDM Theme Manager - Live Preview Overlay
Floating, Always-On-Top overlay widget displayed during live SDDM greeter preview
so users can easily exit the full-screen greeter with one click or pressing Escape.
"""

from PySide6.QtCore import QPoint, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)


class PreviewExitOverlay(QWidget):
    """Floating top-level bar always visible on top of full-screen sddm-greeter."""

    exit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SDDM Preview Controller")
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint
            | Qt.FramelessWindowHint
            | Qt.Window
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_AlwaysShowToolTips, True)

        self._drag_pos = QPoint()
        self._init_ui()

        # Keyboard shortcuts: Esc or Q exits preview
        self.shortcut_esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.shortcut_esc.activated.connect(self._on_exit_clicked)

        self.shortcut_q = QShortcut(QKeySequence(Qt.Key_Q), self)
        self.shortcut_q.activated.connect(self._on_exit_clicked)

        # Repeating timer to ensure overlay stays above greeter window on Wayland/X11
        self._stay_on_top_timer = QTimer(self)
        self._stay_on_top_timer.setInterval(750)
        self._stay_on_top_timer.timeout.connect(self._ensure_on_top)

    def _init_ui(self):
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(0)

        # Container Pill
        self.pill = QFrame()
        self.pill.setStyleSheet(
            "QFrame {"
            "  background-color: rgba(26, 27, 38, 0.96);"
            "  border: 2px solid #f7768e;"
            "  border-radius: 22px;"
            "}"
        )
        pill_layout = QHBoxLayout(self.pill)
        pill_layout.setContentsMargins(18, 8, 10, 8)
        pill_layout.setSpacing(14)

        # Status indicator dot and text
        lbl_status = QLabel("● Live SDDM Preview Active")
        lbl_status.setStyleSheet("color: #7aa2f7; font-size: 13px; font-weight: bold; background: transparent;")
        pill_layout.addWidget(lbl_status)

        # Prominent Exit Button
        self.btn_exit = QPushButton("✕ Exit Preview (Esc)")
        self.btn_exit.setCursor(Qt.PointingHandCursor)
        self.btn_exit.setStyleSheet(
            "QPushButton {"
            "  background-color: #f7768e;"
            "  color: #ffffff;"
            "  border: none;"
            "  border-radius: 15px;"
            "  padding: 8px 18px;"
            "  font-weight: bold;"
            "  font-size: 13px;"
            "}"
            "QPushButton:hover {"
            "  background-color: #ff5577;"
            "}"
            "QPushButton:pressed {"
            "  background-color: #db4b4b;"
            "}"
        )
        self.btn_exit.clicked.connect(self._on_exit_clicked)
        pill_layout.addWidget(self.btn_exit)

        root_layout.addWidget(self.pill)

    def show_top_center(self):
        """Positions overlay in top-center area and raises it on top of greeter."""
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.geometry()
            self.adjustSize()
            x = geom.x() + (geom.width() - self.width()) // 2
            y = geom.y() + 20
            self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()
        self._stay_on_top_timer.start()

    def show_top_right(self):
        """Backwards-compatible alias for positioning overlay."""
        self.show_top_center()

    def hide(self):
        self._stay_on_top_timer.stop()
        super().hide()

    def _ensure_on_top(self):
        if self.isVisible():
            self.raise_()

    def _on_exit_clicked(self):
        self._stay_on_top_timer.stop()
        self.exit_requested.emit()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Escape, Qt.Key_Q):
            self._on_exit_clicked()
            event.accept()
        else:
            super().keyPressEvent(event)

    # Enable dragging overlay if it covers part of the greeter
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
