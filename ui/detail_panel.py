"""
SDDM Theme Manager - Theme Detail Panel
Displays comprehensive metadata and action controls for the selected theme:
Preview toggle, Apply, Background selection/reset, Removal, and Directory inspection.
"""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.theme_scanner import Theme


class DetailPanel(QFrame):
    """Right-side panel with preview image, metadata, and actions."""

    preview_clicked = Signal(object)  # Theme
    apply_clicked = Signal(object)  # Theme
    sync_clicked = Signal(object)  # Theme
    set_background_clicked = Signal(object)  # Theme
    reset_background_clicked = Signal(object)  # Theme
    remove_clicked = Signal(object)  # Theme
    open_folder_clicked = Signal(object)  # Theme
    sync_desktop_clicked = Signal(object)  # Theme
    tweak_clicked = Signal(object)  # Theme
    lint_clicked = Signal(object)  # Theme
    export_clicked = Signal(object)  # Theme
    edit_clicked = Signal(object)  # Theme

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_theme: Optional[Theme] = None
        self.is_preview_running: bool = False

        self.setMinimumWidth(320)
        self.setMaximumWidth(420)
        self.setObjectName("detailPanel")

        self._init_ui()

    def _init_ui(self):
        panel_layout = QVBoxLayout(self)
        panel_layout.setContentsMargins(16, 16, 16, 16)
        panel_layout.setSpacing(12)

        # Scrollable content for metadata
        self.scroll_content = QScrollArea()
        self.scroll_content.setWidgetResizable(True)
        self.scroll_content.setFrameShape(QFrame.NoFrame)
        self.scroll_content.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(0, 0, 4, 0)
        self.content_layout.setSpacing(10)

        # 1. Preview Banner Image
        self.preview_image = QLabel()
        self.preview_image.setFixedHeight(180)
        self.preview_image.setAlignment(Qt.AlignCenter)
        self.preview_image.setStyleSheet("border-radius: 8px; background-color: #16161e;")
        self.content_layout.addWidget(self.preview_image)

        # 2. Header: Title + Active Badge
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        self.lbl_title = QLabel("Select a Theme")
        self.lbl_title.setObjectName("themeTitle")
        self.lbl_title.setWordWrap(True)
        header_layout.addWidget(self.lbl_title)

        self.lbl_active_badge = QLabel("ACTIVE")
        self.lbl_active_badge.setStyleSheet(
            "background-color: #10b981; color: #ffffff; font-size: 11px; font-weight: bold; "
            "border-radius: 4px; padding: 3px 7px;"
        )
        self.lbl_active_badge.setVisible(False)
        header_layout.addWidget(self.lbl_active_badge)
        header_layout.addStretch()

        self.content_layout.addLayout(header_layout)

        # 3. Description
        self.lbl_desc = QLabel("Theme details and options will be displayed here.")
        self.lbl_desc.setObjectName("themeDesc")
        self.lbl_desc.setWordWrap(True)
        self.content_layout.addWidget(self.lbl_desc)

        # 4. Metadata Box
        self.meta_frame = QFrame()
        self.meta_frame.setStyleSheet("background-color: #1a1b26; border-radius: 6px; padding: 10px;")
        meta_layout = QVBoxLayout(self.meta_frame)
        meta_layout.setSpacing(6)
        meta_layout.setContentsMargins(8, 8, 8, 8)

        self.lbl_meta_qt = self._create_meta_row("Qt Version:", meta_layout)
        self.lbl_meta_type = self._create_meta_row("Type:", meta_layout)
        self.lbl_meta_location = self._create_meta_row("Location:", meta_layout)
        self.lbl_meta_system = self._create_meta_row("SDDM System:", meta_layout)
        self.lbl_meta_path = self._create_meta_row("Path:", meta_layout)
        self.lbl_meta_bg = self._create_meta_row("Background:", meta_layout)

        self.content_layout.addWidget(self.meta_frame)
        self.content_layout.addStretch()

        self.scroll_content.setWidget(content_widget)
        panel_layout.addWidget(self.scroll_content)

        # 5. Bottom Actions Area
        actions_box = QVBoxLayout()
        actions_box.setSpacing(8)

        # Preview & Apply row
        main_btns_layout = QHBoxLayout()
        main_btns_layout.setSpacing(8)

        self.btn_preview = QPushButton("Live Preview")
        self.btn_preview.setCursor(Qt.PointingHandCursor)
        self.btn_preview.clicked.connect(self._on_preview_clicked)
        main_btns_layout.addWidget(self.btn_preview)

        self.btn_apply = QPushButton("Apply Theme")
        self.btn_apply.setObjectName("primaryBtn")
        self.btn_apply.setCursor(Qt.PointingHandCursor)
        self.btn_apply.clicked.connect(self._on_apply_clicked)
        main_btns_layout.addWidget(self.btn_apply)

        actions_box.addLayout(main_btns_layout)

        # Sync Theme to System Button
        self.btn_sync = QPushButton("Sync to SDDM (/usr/share)")
        self.btn_sync.setCursor(Qt.PointingHandCursor)
        self.btn_sync.setStyleSheet("background-color: #2e3c64; color: #7aa2f7; border: 1px solid #3d59a1; border-radius: 4px; padding: 5px;")
        self.btn_sync.clicked.connect(self._on_sync_clicked)
        actions_box.addWidget(self.btn_sync)

        # Background buttons row
        bg_btns_layout = QHBoxLayout()
        bg_btns_layout.setSpacing(8)

        self.btn_set_bg = QPushButton("Set Background...")
        self.btn_set_bg.setCursor(Qt.PointingHandCursor)
        self.btn_set_bg.clicked.connect(self._on_set_background_clicked)
        bg_btns_layout.addWidget(self.btn_set_bg)

        self.btn_reset_bg = QPushButton("Reset BG")
        self.btn_reset_bg.setCursor(Qt.PointingHandCursor)
        self.btn_reset_bg.clicked.connect(self._on_reset_background_clicked)
        bg_btns_layout.addWidget(self.btn_reset_bg)

        actions_box.addLayout(bg_btns_layout)

        # Desktop Sync button
        self.btn_sync_desktop = QPushButton("🔄 Match Desktop Wallpaper")
        self.btn_sync_desktop.setCursor(Qt.PointingHandCursor)
        self.btn_sync_desktop.clicked.connect(self._on_sync_desktop_clicked)
        actions_box.addWidget(self.btn_sync_desktop)

        # Advanced tools: Editor, Tweaker, Linter, Exporter
        tools_layout = QHBoxLayout()
        tools_layout.setSpacing(6)

        self.btn_edit_theme = QPushButton("✏️ Edit Files…")
        self.btn_edit_theme.setCursor(Qt.PointingHandCursor)
        self.btn_edit_theme.clicked.connect(self._on_edit_theme_clicked)
        tools_layout.addWidget(self.btn_edit_theme)

        self.btn_tweak = QPushButton("⚙️ Customize…")
        self.btn_tweak.setCursor(Qt.PointingHandCursor)
        self.btn_tweak.clicked.connect(self._on_tweak_clicked)
        tools_layout.addWidget(self.btn_tweak)

        actions_box.addLayout(tools_layout)

        tools_layout2 = QHBoxLayout()
        tools_layout2.setSpacing(6)

        self.btn_lint = QPushButton("🛡️ Check")
        self.btn_lint.setCursor(Qt.PointingHandCursor)
        self.btn_lint.clicked.connect(self._on_lint_clicked)
        tools_layout2.addWidget(self.btn_lint)

        self.btn_export = QPushButton("📦 Export")
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.clicked.connect(self._on_export_clicked)
        tools_layout2.addWidget(self.btn_export)

        actions_box.addLayout(tools_layout2)

        # Secondary Actions (Open folder, Remove)
        secondary_layout = QHBoxLayout()
        secondary_layout.setSpacing(8)

        self.btn_open_folder = QPushButton("Open Folder")
        self.btn_open_folder.clicked.connect(self._on_open_folder_clicked)
        secondary_layout.addWidget(self.btn_open_folder)

        self.btn_remove = QPushButton("Remove")
        self.btn_remove.setObjectName("dangerBtn")
        self.btn_remove.clicked.connect(self._on_remove_clicked)
        secondary_layout.addWidget(self.btn_remove)

        actions_box.addLayout(secondary_layout)

        panel_layout.addLayout(actions_box)

    def _create_meta_row(self, title: str, parent_layout: QVBoxLayout) -> QLabel:
        row = QHBoxLayout()
        row.setSpacing(6)
        lbl_k = QLabel(title)
        lbl_k.setStyleSheet("color: #787c99; font-weight: 500; font-size: 11px;")
        lbl_k.setFixedWidth(75)
        lbl_v = QLabel("-")
        lbl_v.setStyleSheet("color: #c0caf5; font-size: 11px;")
        lbl_v.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lbl_v.setWordWrap(True)
        row.addWidget(lbl_k)
        row.addWidget(lbl_v, 1)
        parent_layout.addLayout(row)
        return lbl_v

    def set_theme(self, theme: Optional[Theme]):
        """Updates panel content with the specified theme's details."""
        self.current_theme = theme
        if not theme:
            self.lbl_title.setText("Select a Theme")
            self.lbl_desc.setText("Select a theme from the grid to view details and options.")
            self.lbl_active_badge.setVisible(False)
            self.lbl_meta_qt.setText("-")
            self.lbl_meta_type.setText("-")
            self.lbl_meta_location.setText("-")
            self.lbl_meta_system.setText("-")
            self.lbl_meta_path.setText("-")
            self.lbl_meta_bg.setText("-")
            self.preview_image.setPixmap(QPixmap())
            self.btn_apply.setEnabled(False)
            self.btn_preview.setEnabled(False)
            self.btn_sync.setEnabled(False)
            self.btn_set_bg.setEnabled(False)
            self.btn_reset_bg.setEnabled(False)
            self.btn_remove.setEnabled(False)
            self.btn_open_folder.setEnabled(False)
            self.btn_edit_theme.setEnabled(False)
            self.btn_tweak.setEnabled(False)
            self.btn_lint.setEnabled(False)
            self.btn_export.setEnabled(False)
            self.btn_sync_desktop.setEnabled(False)
            return

        self.lbl_title.setText(theme.name)
        self.lbl_desc.setText(theme.description or "No description provided.")
        self.lbl_active_badge.setVisible(theme.is_active)

        self.lbl_meta_qt.setText(theme.display_qt_version)
        self.lbl_meta_type.setText(theme.theme_type)
        self.lbl_meta_location.setText(f"{theme.location_badge} Theme")

        # System installation status
        if theme.is_system or theme.is_installed_in_system:
            self.lbl_meta_system.setText("Installed in /usr/share/sddm/themes")
            self.lbl_meta_system.setStyleSheet("color: #10b981; font-size: 11px;")
        else:
            self.lbl_meta_system.setText("User only (needs sync for SDDM)")
            self.lbl_meta_system.setStyleSheet("color: #e0af68; font-size: 11px;")

        self.lbl_meta_path.setText(str(theme.path))

        # Background status
        if theme.custom_background:
            bg_name = Path(theme.custom_background).name
            self.lbl_meta_bg.setText(f"Custom ({bg_name})")
            self.btn_reset_bg.setEnabled(True)
        elif theme.default_background:
            bg_name = Path(theme.default_background).name
            self.lbl_meta_bg.setText(f"Default ({bg_name})")
            self.btn_reset_bg.setEnabled(False)
        else:
            self.lbl_meta_bg.setText("Theme Default")
            self.btn_reset_bg.setEnabled(False)

        # Render preview banner
        self._update_preview_banner(theme)

        # Button states
        self.btn_preview.setEnabled(True)
        self.btn_edit_theme.setEnabled(True)
        self.btn_set_bg.setEnabled(True)
        self.btn_sync_desktop.setEnabled(True)
        self.btn_tweak.setEnabled(True)
        self.btn_lint.setEnabled(True)
        self.btn_export.setEnabled(True)
        self.btn_open_folder.setEnabled(True)
        self.btn_remove.setEnabled(True)

        # Sync button visibility
        if not theme.is_system:
            self.btn_sync.setVisible(True)
            self.btn_sync.setEnabled(True)
            if theme.is_installed_in_system:
                self.btn_sync.setText("Resync to SDDM (/usr/share)")
            else:
                self.btn_sync.setText("Sync to SDDM (/usr/share)")
        else:
            self.btn_sync.setVisible(False)

        # Apply button state
        if theme.is_active:
            if getattr(theme, "is_missing_from_system", False):
                self.lbl_active_badge.setText("ACTIVE (MISSING IN SDDM!)")
                self.lbl_active_badge.setStyleSheet(
                    "background-color: #f7768e; color: #ffffff; font-size: 10px; font-weight: bold; "
                    "border-radius: 4px; padding: 3px 6px;"
                )
                self.btn_apply.setEnabled(True)
                self.btn_apply.setText("⚠️ Fix & Sync to SDDM")
                self.btn_apply.setStyleSheet("background-color: #e0af68; color: #1a1b26; font-weight: bold;")
            else:
                self.lbl_active_badge.setText("ACTIVE")
                self.lbl_active_badge.setStyleSheet(
                    "background-color: #10b981; color: #ffffff; font-size: 11px; font-weight: bold; "
                    "border-radius: 4px; padding: 3px 7px;"
                )
                self.btn_apply.setEnabled(True)
                self.btn_apply.setText("Re-apply / Resync Theme")
                self.btn_apply.setStyleSheet("")
        else:
            self.lbl_active_badge.setText("ACTIVE")
            self.lbl_active_badge.setStyleSheet(
                "background-color: #10b981; color: #ffffff; font-size: 11px; font-weight: bold; "
                "border-radius: 4px; padding: 3px 7px;"
            )
            self.btn_apply.setEnabled(True)
            self.btn_apply.setText("Apply Theme")
            self.btn_apply.setStyleSheet("")

    def _update_preview_banner(self, theme: Theme):
        target_size = QSize(350, 180)
        img_path = theme.preview_path
        if not img_path and theme.custom_background:
            img_path = Path(theme.custom_background)
        if not img_path and theme.default_background:
            img_path = Path(theme.default_background)

        if img_path and img_path.exists():
            try:
                pix = QPixmap(str(img_path))
                if not pix.isNull():
                    scaled = pix.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.preview_image.setPixmap(scaled)
                    return
            except Exception:
                pass

        # Stylized placeholder
        pixmap = QPixmap(target_size)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        gradient = QLinearGradient(0, 0, target_size.width(), target_size.height())
        gradient.setColorAt(0.0, QColor(36, 40, 59))
        gradient.setColorAt(1.0, QColor(26, 27, 38))
        painter.fillRect(QRect(0, 0, target_size.width(), target_size.height()), gradient)

        painter.setPen(QPen(QColor(65, 72, 104), 2))
        painter.drawRoundedRect(QRect(15, 15, target_size.width() - 30, target_size.height() - 30), 8, 8)

        painter.setPen(QColor(192, 202, 245))
        painter.setFont(QFont("sans-serif", 13, QFont.Bold))
        painter.drawText(QRect(0, 60, target_size.width(), 30), Qt.AlignCenter, theme.name)

        painter.setPen(QColor(122, 162, 247))
        painter.setFont(QFont("sans-serif", 10))
        painter.drawText(QRect(0, 95, target_size.width(), 25), Qt.AlignCenter, f"{theme.display_qt_version} Greeter")

        painter.end()
        self.preview_image.setPixmap(pixmap)

    def set_preview_running(self, running: bool):
        """Toggles Preview button appearance when live greeter is active."""
        self.is_preview_running = running
        if running:
            self.btn_preview.setText("Close Preview")
            self.btn_preview.setObjectName("previewActiveBtn")
        else:
            self.btn_preview.setText("Live Preview")
            self.btn_preview.setObjectName("")
        self.btn_preview.style().unpolish(self.btn_preview)
        self.btn_preview.style().polish(self.btn_preview)

    def _on_preview_clicked(self):
        if self.current_theme:
            self.preview_clicked.emit(self.current_theme)

    def _on_apply_clicked(self):
        if self.current_theme:
            self.apply_clicked.emit(self.current_theme)

    def _on_sync_clicked(self):
        if self.current_theme:
            self.sync_clicked.emit(self.current_theme)

    def _on_set_background_clicked(self):
        if self.current_theme:
            self.set_background_clicked.emit(self.current_theme)

    def _on_reset_background_clicked(self):
        if self.current_theme:
            self.reset_background_clicked.emit(self.current_theme)

    def _on_remove_clicked(self):
        if self.current_theme:
            self.remove_clicked.emit(self.current_theme)

    def _on_open_folder_clicked(self):
        if self.current_theme:
            self.open_folder_clicked.emit(self.current_theme)

    def _on_sync_desktop_clicked(self):
        if self.current_theme:
            self.sync_desktop_clicked.emit(self.current_theme)

    def _on_tweak_clicked(self):
        if self.current_theme:
            self.tweak_clicked.emit(self.current_theme)

    def _on_lint_clicked(self):
        if self.current_theme:
            self.lint_clicked.emit(self.current_theme)

    def _on_export_clicked(self):
        if self.current_theme:
            self.export_clicked.emit(self.current_theme)

    def _on_edit_theme_clicked(self):
        if self.current_theme:
            self.edit_clicked.emit(self.current_theme)
