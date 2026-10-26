"""
SDDM Theme Manager - Install Theme Chooser Dialog
Provides a dual-card chooser dialog:
- Card 1: Create Your Own (Minimal, Custom Wallpaper, or Boilerplate modes -> Theme Editor)
- Card 2: Install from Archive (file picker -> extraction & validation)
Includes integrated interactive tutorials for theme files and creation template modes.
"""

import re
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QRegularExpression, QSize, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QIcon, QPainter, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QStackedWidget,
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
    Supports Minimal (asset-free), Custom Wallpaper, and Boilerplate creation modes.
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

        # Header with Tutorial / Info action
        header_top_layout = QHBoxLayout()
        title_lbl = QLabel("Install Theme", self)
        title_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        header_top_layout.addWidget(title_lbl)
        header_top_layout.addStretch()

        self.btn_tutorial = QPushButton("📖 Tutorial / Info", self)
        self.btn_tutorial.setToolTip("Learn about theme files and template modes (60-word interactive guide)")
        self.btn_tutorial.setCursor(Qt.PointingHandCursor)
        self.btn_tutorial.clicked.connect(lambda: self._open_tutorial(initial_category="files"))
        header_top_layout.addWidget(self.btn_tutorial)
        main_layout.addLayout(header_top_layout)

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
            "Scaffold a clean template\nand open the live editor",
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

        # Inline Form Area for "Create Your Own"
        self.create_form_frame = QFrame(self)
        self.create_form_frame.setStyleSheet(
            "QFrame {"
            "  background-color: #1f2335;"
            "  border: 1px solid #3b4261;"
            "  border-radius: 10px;"
            "  padding: 14px;"
            "}"
            "QRadioButton {"
            "  color: #c0caf5;"
            "  font-size: 12px;"
            "  font-weight: 500;"
            "  spacing: 6px;"
            "}"
            "QRadioButton:checked {"
            "  color: #7aa2f7;"
            "  font-weight: bold;"
            "}"
            "QCheckBox {"
            "  color: #9aa5ce;"
            "  font-size: 12px;"
            "  spacing: 6px;"
            "}"
            "QCheckBox:checked {"
            "  color: #c0caf5;"
            "}"
        )
        self.create_form_frame.setVisible(False)

        form_vlayout = QVBoxLayout(self.create_form_frame)
        form_vlayout.setSpacing(10)

        # 1. Theme Identifier Name
        prompt_lbl = QLabel("<b>Theme Identifier Name:</b>", self.create_form_frame)
        form_vlayout.addWidget(prompt_lbl)

        self.txt_theme_name = QLineEdit(self.create_form_frame)
        self.txt_theme_name.setPlaceholderText("e.g. my-custom-sddm-theme")
        self.txt_theme_name.textChanged.connect(self._validate_theme_name)
        form_vlayout.addWidget(self.txt_theme_name)

        # Red error feedback label
        self.lbl_error = QLabel("", self.create_form_frame)
        self.lbl_error.setStyleSheet("color: #f38ba8; font-size: 12px;")
        form_vlayout.addWidget(self.lbl_error)

        # 2. Template Creation Mode Header with Guide Button
        mode_hdr_layout = QHBoxLayout()
        mode_hdr = QLabel("<b>Template Creation Mode:</b>", self.create_form_frame)
        mode_hdr_layout.addWidget(mode_hdr)
        mode_hdr_layout.addStretch()

        self.btn_mode_guide = QPushButton("📖 Mode Guide & Tutorial", self.create_form_frame)
        self.btn_mode_guide.setStyleSheet("padding: 3px 8px; font-size: 11px;")
        self.btn_mode_guide.setCursor(Qt.PointingHandCursor)
        self.btn_mode_guide.clicked.connect(lambda: self._open_tutorial(initial_category="modes"))
        mode_hdr_layout.addWidget(self.btn_mode_guide)
        form_vlayout.addLayout(mode_hdr_layout)

        # Mode radio options
        mode_radio_layout = QHBoxLayout()
        mode_radio_layout.setSpacing(14)

        self.btn_group_mode = QButtonGroup(self)

        self.radio_minimal = QRadioButton("🧼 Minimal (Asset-Free)", self.create_form_frame)
        self.radio_minimal.setChecked(True)
        self.btn_group_mode.addButton(self.radio_minimal, 0)
        mode_radio_layout.addWidget(self.radio_minimal)

        self.radio_custom = QRadioButton("🖼️ Custom Wallpaper", self.create_form_frame)
        self.btn_group_mode.addButton(self.radio_custom, 1)
        mode_radio_layout.addWidget(self.radio_custom)

        self.radio_boilerplate = QRadioButton("🎨 Boilerplate Starter", self.create_form_frame)
        self.btn_group_mode.addButton(self.radio_boilerplate, 2)
        mode_radio_layout.addWidget(self.radio_boilerplate)

        form_vlayout.addLayout(mode_radio_layout)

        # Dynamic Mode Details Area
        self.mode_context_stack = QStackedWidget(self.create_form_frame)
        self.mode_context_stack.setStyleSheet(
            "QStackedWidget {"
            "  background-color: #16161e;"
            "  border: 1px solid #292e42;"
            "  border-radius: 6px;"
            "  padding: 8px;"
            "}"
        )

        # Page 0: Minimal Code Mode
        page_minimal = QWidget()
        min_layout = QVBoxLayout(page_minimal)
        min_layout.setContentsMargins(6, 6, 6, 6)
        lbl_min_hint = QLabel(
            "💡 <b>Asset-Free:</b> Scaffolds clean code files (Main.qml, theme.conf, metadata). "
            "Zero dummy images created. Greeter renders an aesthetic procedural dark gradient fallback.",
            page_minimal,
        )
        lbl_min_hint.setWordWrap(True)
        lbl_min_hint.setStyleSheet("color: #a6e3a1; font-size: 12px; background: transparent;")
        min_layout.addWidget(lbl_min_hint)
        self.mode_context_stack.addWidget(page_minimal)

        # Page 1: Custom Wallpaper Mode
        page_custom = QWidget()
        cust_layout = QVBoxLayout(page_custom)
        cust_layout.setContentsMargins(6, 6, 6, 6)
        cust_layout.setSpacing(6)
        lbl_cust_hint = QLabel("Select background image to import directly into theme:", page_custom)
        lbl_cust_hint.setStyleSheet("color: #7aa2f7; font-size: 12px; background: transparent;")
        cust_layout.addWidget(lbl_cust_hint)

        cust_file_row = QHBoxLayout()
        self.txt_custom_wallpaper = QLineEdit(page_custom)
        self.txt_custom_wallpaper.setPlaceholderText("Select image (.png, .jpg, .webp)…")
        cust_file_row.addWidget(self.txt_custom_wallpaper, 1)

        self.btn_browse_custom = QPushButton("📂 Browse…", page_custom)
        self.btn_browse_custom.setCursor(Qt.PointingHandCursor)
        self.btn_browse_custom.clicked.connect(self._browse_custom_wallpaper)
        cust_file_row.addWidget(self.btn_browse_custom)
        cust_layout.addLayout(cust_file_row)
        self.mode_context_stack.addWidget(page_custom)

        # Page 2: Boilerplate Starter Mode
        page_boiler = QWidget()
        boiler_layout = QVBoxLayout(page_boiler)
        boiler_layout.setContentsMargins(6, 6, 6, 6)
        lbl_boiler_hint = QLabel(
            "💡 <b>Boilerplate:</b> Generates sample 1920×1080 background.png and matching preview.png assets.",
            page_boiler,
        )
        lbl_boiler_hint.setWordWrap(True)
        lbl_boiler_hint.setStyleSheet("color: #fab387; font-size: 12px; background: transparent;")
        boiler_layout.addWidget(lbl_boiler_hint)
        self.mode_context_stack.addWidget(page_boiler)

        form_vlayout.addWidget(self.mode_context_stack)
        self.btn_group_mode.idToggled.connect(self._on_mode_radio_toggled)

        # 3. Checkbox: Optional preview.png generation
        self.chk_generate_preview = QCheckBox(
            "Generate preview.png thumbnail for theme manager grids", self.create_form_frame
        )
        self.chk_generate_preview.setChecked(False)
        form_vlayout.addWidget(self.chk_generate_preview)

        # 4. Form Action Buttons
        action_row = QHBoxLayout()
        action_row.addStretch()

        btn_cancel_create = QPushButton("Cancel", self.create_form_frame)
        btn_cancel_create.clicked.connect(self._toggle_create_form)
        action_row.addWidget(btn_cancel_create)

        self.btn_create_scaffold = QPushButton("Create Theme & Open Editor", self.create_form_frame)
        self.btn_create_scaffold.setObjectName("primaryActionBtn")
        self.btn_create_scaffold.setEnabled(False)
        self.btn_create_scaffold.clicked.connect(self._on_create_confirmed)
        action_row.addWidget(self.btn_create_scaffold)

        form_vlayout.addLayout(action_row)

        main_layout.addWidget(self.create_form_frame)

        # Bottom dialog row
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()

        btn_cancel = QPushButton("Close", self)
        btn_cancel.clicked.connect(self.reject)
        bottom_row.addWidget(btn_cancel)

        main_layout.addLayout(bottom_row)

    def _on_mode_radio_toggled(self, button_id: int, checked: bool):
        if not checked:
            return
        self.mode_context_stack.setCurrentIndex(button_id)
        if button_id == 0:  # Minimal
            self.chk_generate_preview.setChecked(False)
        elif button_id == 1:  # Custom
            self.chk_generate_preview.setChecked(True)
        elif button_id == 2:  # Boilerplate
            self.chk_generate_preview.setChecked(True)

    def _browse_custom_wallpaper(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Background Wallpaper Image",
            str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.webp *.svg);;All Files (*)",
        )
        if file_path:
            self.txt_custom_wallpaper.setText(file_path)
            self._validate_theme_name(self.txt_theme_name.text())

    def _toggle_create_form(self):
        """Shows and focuses the inline creation form."""
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
        """Scaffolds new theme with chosen mode and immediately launches Theme Editor."""
        name = self.txt_theme_name.text().strip()
        if not name:
            return

        mode_id = self.btn_group_mode.checkedId()
        mode_str = "minimal"
        custom_img = None
        if mode_id == 1:
            mode_str = "custom"
            custom_img = self.txt_custom_wallpaper.text().strip() or None
        elif mode_id == 2:
            mode_str = "boilerplate"

        generate_preview = self.chk_generate_preview.isChecked()

        ok, theme_dir, msg = ThemeWriter.scaffold_theme(
            theme_name=name,
            mode=mode_str,
            custom_wallpaper_path=custom_img,
            generate_preview=generate_preview,
        )
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
                f"Theme '{installed_path.name}' installed successfully into {installed_path.parent}.",
            )
            self.accept()
        elif not ok and "cancelled" not in msg.lower():
            pass

    def _open_tutorial(self, initial_category: str = "files"):
        """Opens the interactive SDDM theme files or template modes tutorial dialog."""
        from ui.theme_tutorial_dialog import ThemeTutorialDialog

        dlg = ThemeTutorialDialog(None, self, initial_category=initial_category)
        dlg.exec()
