"""
SDDM Theme Manager - Install Theme Chooser Dialog
Provides a dual-card chooser dialog:
- Card 1: Create Your Own (inline validation & scaffolding -> Theme Editor)
- Card 2: Install from Archive (file picker -> extraction & validation)
"""

import re
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QRegularExpression, QSize, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QIcon, QPainter, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.theme_scanner import ThemeScanner
from ui.archive_installer import ArchiveInstaller
from ui.theme_editor import ThemeEditor
from ui.theme_writer import ThemeWriter

NAME_REGEX = re.compile(r"^[a-z0-9][a-z0-9-]{0,48}[a-z0-9]$")


class ClickableCard(QFrame):
    """Interactive card with hover styling and clicked signal."""

    clicked = Signal()

    def __init__(self, icon_text: str, title: str, subtitle: str, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedWidth(280)
        self.setMinimumHeight(220)

        self.setStyleSheet(
            "ClickableCard {"
            "  background-color: #1f2335;"
            "  border: 2px solid #3b4261;"
            "  border-radius: 12px;"
            "  padding: 16px;"
            "}"
            "ClickableCard:hover {"
            "  background-color: #24283b;"
            "  border-color: #7aa2f7;"
            "}"
        )

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)

        lbl_icon = QLabel(icon_text, self)
        lbl_icon.setAlignment(Qt.AlignCenter)
        lbl_icon.setStyleSheet("font-size: 48px; background: transparent;")
        layout.addWidget(lbl_icon)

        lbl_title = QLabel(title, self)
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff; background: transparent;")
        layout.addWidget(lbl_title)

        lbl_sub = QLabel(subtitle, self)
        lbl_sub.setAlignment(Qt.AlignCenter)
        lbl_sub.setWordWrap(True)
        lbl_sub.setStyleSheet("font-size: 12px; color: #9aa5ce; background: transparent; line-height: 1.4;")
        layout.addWidget(lbl_sub)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class InstallDialog(QDialog):
    """
    Modal chooser dialog:
    [ Create Your Own ] | [ Install from Archive ]
    """

    theme_installed = Signal(Path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.installed_path: Optional[Path] = None

        self.setWindowTitle("Install Theme")
        self.setFixedWidth(660)
        self.setModal(True)

        self.setStyleSheet(
            "QDialog {"
            "  background-color: #1a1b26;"
            "  color: #c0caf5;"
            "}"
            "QLabel {"
            "  color: #c0caf5;"
            "}"
            "QLineEdit {"
            "  background-color: #24283b;"
            "  color: #c0caf5;"
            "  border: 1px solid #3b4261;"
            "  border-radius: 6px;"
            "  padding: 8px 12px;"
            "  font-size: 13px;"
            "}"
            "QLineEdit:focus {"
            "  border-color: #7aa2f7;"
            "  background-color: #1f2335;"
            "}"
            "QPushButton {"
            "  background-color: #24283b;"
            "  color: #c0caf5;"
            "  border: 1px solid #3b4261;"
            "  border-radius: 6px;"
            "  padding: 8px 16px;"
            "  font-weight: 500;"
            "}"
            "QPushButton:hover {"
            "  background-color: #2f354f;"
            "  border-color: #7aa2f7;"
            "  color: #ffffff;"
            "}"
            "QPushButton#primaryActionBtn {"
            "  background-color: #3d59a1;"
            "  color: #ffffff;"
            "  border: 1px solid #7aa2f7;"
            "  font-weight: 600;"
            "}"
            "QPushButton#primaryActionBtn:hover {"
            "  background-color: #7aa2f7;"
            "  color: #1a1b26;"
            "}"
            "QPushButton#primaryActionBtn:disabled {"
            "  background-color: #1f2335;"
            "  color: #565f89;"
            "  border-color: #292e42;"
            "}"
        )

        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(18)

        # Header
        title_lbl = QLabel("Install Theme", self)
        title_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        main_layout.addWidget(title_lbl)

        desc_lbl = QLabel("Choose how you would like to add a new SDDM theme:", self)
        desc_lbl.setStyleSheet("font-size: 13px; color: #9aa5ce;")
        main_layout.addWidget(desc_lbl)

        # Cards container
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)

        # Left Card: Create Your Own
        self.card_create = ClickableCard(
            "📁",
            "Create Your Own",
            "Scaffold a new theme.conf\nand open the live editor",
            self,
        )
        self.card_create.clicked.connect(self._toggle_create_form)
        cards_layout.addWidget(self.card_create)

        # Right Card: Install from Archive
        self.card_archive = ClickableCard(
            "📦",
            "Install from Archive",
            "Extract a .zip, .tar.gz\nor .tgz into themes directory",
            self,
        )
        self.card_archive.clicked.connect(self.install_from_archive)
        cards_layout.addWidget(self.card_archive)

        main_layout.addLayout(cards_layout)

        # Inline Name Prompt Area for "Create Your Own"
        self.create_form_frame = QFrame(self)
        self.create_form_frame.setStyleSheet(
            "QFrame {"
            "  background-color: #1f2335;"
            "  border: 1px solid #3b4261;"
            "  border-radius: 8px;"
            "  padding: 12px;"
            "}"
        )
        self.create_form_frame.setVisible(False)

        form_vlayout = QVBoxLayout(self.create_form_frame)
        form_vlayout.setSpacing(8)

        prompt_lbl = QLabel("<b>Theme Identifier Name:</b>", self.create_form_frame)
        form_vlayout.addWidget(prompt_lbl)

        input_row = QHBoxLayout()
        self.txt_theme_name = QLineEdit(self.create_form_frame)
        self.txt_theme_name.setPlaceholderText("e.g. my-custom-sddm-theme")
        self.txt_theme_name.textChanged.connect(self._validate_theme_name)
        input_row.addWidget(self.txt_theme_name, 1)

        self.btn_create_scaffold = QPushButton("Create", self.create_form_frame)
        self.btn_create_scaffold.setObjectName("primaryActionBtn")
        self.btn_create_scaffold.setEnabled(False)
        self.btn_create_scaffold.clicked.connect(self._on_create_confirmed)
        input_row.addWidget(self.btn_create_scaffold)

        form_vlayout.addLayout(input_row)

        # Red error feedback label
        self.lbl_error = QLabel("", self.create_form_frame)
        self.lbl_error.setStyleSheet("color: #f38ba8; font-size: 12px;")
        form_vlayout.addWidget(self.lbl_error)

        main_layout.addWidget(self.create_form_frame)

        # Bottom buttons
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()

        btn_cancel = QPushButton("Cancel", self)
        btn_cancel.clicked.connect(self.reject)
        bottom_row.addWidget(btn_cancel)

        main_layout.addLayout(bottom_row)

    def _toggle_create_form(self):
        """Shows and focuses the inline name prompt."""
        is_visible = self.create_form_frame.isVisible()
        self.create_form_frame.setVisible(not is_visible)
        if not is_visible:
            self.txt_theme_name.setFocus()
            self._validate_theme_name(self.txt_theme_name.text())

    def _validate_theme_name(self, name_text: str):
        """
        Validates theme name:
        - lowercase letters, digits, hyphens only
        - no leading or trailing hyphen
        - 2 to 50 chars
        - must not already exist in /usr/share/sddm/themes or ~/.local/share/sddm/themes
        """
        name = name_text.strip()
        if not name:
            self.lbl_error.setText("Theme name cannot be empty.")
            self.btn_create_scaffold.setEnabled(False)
            return

        if len(name) < 2:
            self.lbl_error.setText("Theme name must be at least 2 characters long.")
            self.btn_create_scaffold.setEnabled(False)
            return

        if len(name) > 50:
            self.lbl_error.setText("Theme name cannot exceed 50 characters.")
            self.btn_create_scaffold.setEnabled(False)
            return

        if not NAME_REGEX.match(name):
            self.lbl_error.setText("Use only lowercase letters, digits, and hyphens (no leading/trailing hyphen).")
            self.btn_create_scaffold.setEnabled(False)
            return

        # Check existing themes
        sys_path = Path("/usr/share/sddm/themes") / name
        user_path = ThemeScanner.get_user_themes_dir() / name

        if sys_path.exists() or user_path.exists():
            self.lbl_error.setText(f"Theme '{name}' already exists on this system.")
            self.btn_create_scaffold.setEnabled(False)
            return

        # Valid input
        self.lbl_error.setText("")
        self.btn_create_scaffold.setEnabled(True)

    def _on_create_confirmed(self):
        """Scaffolds new theme and immediately launches the Theme Editor."""
        name = self.txt_theme_name.text().strip()
        if not name:
            return

        ok, theme_dir, msg = ThemeWriter.scaffold_theme(name)
        if not ok or not theme_dir:
            QMessageBox.critical(self, "Scaffold Failed", f"Could not create theme directory:\n\n{msg}")
            return

        self.installed_path = theme_dir
        self.theme_installed.emit(theme_dir)

        # Open Theme Editor immediately
        editor_dialog = ThemeEditor(theme_dir, self.parent())
        self.accept()
        editor_dialog.exec()

    def install_from_archive(self):
        """Opens file picker and runs archive extraction with conflict checks."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select SDDM Theme Archive",
            str(Path.home()),
            "Archives (*.zip *.tar.gz *.tgz *.tar.xz *.tar.bz2 *.tar);;All Files (*)",
        )
        if not file_path:
            return

        ok, installed_path, msg = ArchiveInstaller.install(
            archive_path=file_path,
            parent_widget=self,
        )

        if ok and installed_path:
            self.installed_path = installed_path
            self.theme_installed.emit(installed_path)
            QMessageBox.information(
                self,
                "Theme Installed",
                f"Theme '{installed_path.name}' installed successfully into {installed_path.parent}."
            )
            self.accept()
        elif not ok and "cancelled" not in msg.lower():
            # Failure message dialog already handled or displayed
            pass
