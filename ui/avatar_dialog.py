"""
SDDM Theme Manager - User Avatar Dialog
GUI for selecting, previewing, and applying user login profile pictures to SDDM.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core.avatar_manager import AvatarManager


class AvatarDialog(QDialog):
    """Dialog to manage SDDM user login icons."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("User Avatar Manager — SDDM")
        self.setFixedSize(360, 420)
        self.selected_image_path: Path | None = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        lbl_title = QLabel("SDDM Login Profile Picture")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #7aa2f7;")
        lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)

        # Circular Avatar Preview Box
        self.lbl_preview = QLabel()
        self.lbl_preview.setFixedSize(140, 140)
        self.lbl_preview.setAlignment(Qt.AlignCenter)
        self.lbl_preview.setStyleSheet("border-radius: 70px; background-color: #1a1b26; border: 2px solid #3d59a1;")

        h_prev = QHBoxLayout()
        h_prev.addStretch()
        h_prev.addWidget(self.lbl_preview)
        h_prev.addStretch()
        layout.addLayout(h_prev)

        # User Selector
        form = QFormLayout()
        self.combo_user = QComboBox()
        self.combo_user.addItems(AvatarManager.get_system_users())
        self.combo_user.currentTextChanged.connect(self._load_current_avatar)
        form.addRow("User Account:", self.combo_user)
        layout.addLayout(form)

        # Choose File Button
        btn_choose = QPushButton(" Select New Image…")
        btn_choose.setCursor(Qt.PointingHandCursor)
        btn_choose.clicked.connect(self._choose_image)
        layout.addWidget(btn_choose)

        layout.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        self.btn_apply = QPushButton("Apply Avatar")
        self.btn_apply.setEnabled(False)
        self.btn_apply.setStyleSheet("background-color: #7aa2f7; color: #1a1b26; font-weight: bold; padding: 6px 14px;")
        self.btn_apply.clicked.connect(self._apply_avatar)
        btn_layout.addWidget(self.btn_apply)

        layout.addLayout(btn_layout)

        # Load initial avatar
        self._load_current_avatar()

    def _load_current_avatar(self):
        user = self.combo_user.currentText()
        avatar_path = AvatarManager.get_user_avatar(user)
        if avatar_path and avatar_path.exists():
            pix = QPixmap(str(avatar_path))
            if not pix.isNull():
                self._set_circular_preview(pix)
                return

        # Fallback empty avatar
        self.lbl_preview.setPixmap(QPixmap())
        self.lbl_preview.setText("No Avatar")

    def _set_circular_preview(self, pixmap: QPixmap):
        size = 140
        scaled = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

        target = QPixmap(size, size)
        target.fill(Qt.transparent)

        painter = QPainter(target)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, scaled)
        painter.end()

        self.lbl_preview.setPixmap(target)

    def _choose_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Profile Picture",
            str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if file_path:
            p = Path(file_path)
            pix = QPixmap(str(p))
            if not pix.isNull():
                self.selected_image_path = p
                self._set_circular_preview(pix)
                self.btn_apply.setEnabled(True)
            else:
                QMessageBox.warning(self, "Invalid Image", "Could not load the chosen image.")

    def _apply_avatar(self):
        if not self.selected_image_path:
            return

        user = self.combo_user.currentText()
        ok, msg = AvatarManager.set_user_avatar(self.selected_image_path, user)
        if ok:
            QMessageBox.information(self, "Avatar Saved", msg)
            self.accept()
        else:
            QMessageBox.critical(self, "Avatar Error", msg)
