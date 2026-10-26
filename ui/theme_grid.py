"""
SDDM Theme Manager - Theme Grid
Interactive grid of theme cards displaying preview thumbnails, names,
badges (Active, Qt version, System/User), and descriptions.
"""

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.theme_scanner import Theme


class ThemeCard(QFrame):
    """Visual card representing a single SDDM theme."""

    clicked = Signal(object)  # Theme
    double_clicked = Signal(object)  # Theme
    context_menu_requested = Signal(object, QPoint)  # Theme, global_pos

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.is_selected = False

        self.setFixedSize(220, 200)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("themeCard")

        self._init_ui()
        self._update_style()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 1. Thumbnail Container
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(204, 115)
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setStyleSheet("border-radius: 6px; background-color: #16161e;")
        self.thumb_label.setPixmap(self._create_thumbnail())
        layout.addWidget(self.thumb_label)

        # 2. Badges Row (Active badge, Qt version, System/User)
        badges_layout = QHBoxLayout()
        badges_layout.setContentsMargins(0, 0, 0, 0)
        badges_layout.setSpacing(4)

        if self.theme.is_active:
            if getattr(self.theme, "is_missing_from_system", False):
                active_badge = QLabel("⚠️ NEEDS SYNC")
                active_badge.setStyleSheet(
                    "background-color: #f7768e; color: #ffffff; font-size: 10px; font-weight: bold; "
                    "border-radius: 3px; padding: 2px 5px;"
                )
                badges_layout.addWidget(active_badge)
            else:
                active_badge = QLabel("ACTIVE")
                active_badge.setStyleSheet(
                    "background-color: #10b981; color: #ffffff; font-size: 10px; font-weight: bold; "
                    "border-radius: 3px; padding: 2px 5px;"
                )
                badges_layout.addWidget(active_badge)

        qt_badge = QLabel(self.theme.display_qt_version)
        qt_badge.setStyleSheet(
            "background-color: #24283b; color: #7aa2f7; font-size: 10px; font-weight: 600; "
            "border: 1px solid #3b4261; border-radius: 3px; padding: 1px 4px;"
        )
        badges_layout.addWidget(qt_badge)

        loc_badge = QLabel(self.theme.location_badge)
        loc_badge.setStyleSheet(
            "background-color: #24283b; color: #9aa5ce; font-size: 10px; "
            "border: 1px solid #3b4261; border-radius: 3px; padding: 1px 4px;"
        )
        badges_layout.addWidget(loc_badge)
        badges_layout.addStretch()
        layout.addLayout(badges_layout)

        # 3. Theme Name
        self.name_label = QLabel(self.theme.name)
        self.name_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #ffffff;")
        self.name_label.setWordWrap(False)
        layout.addWidget(self.name_label)

        # 4. Short Description
        desc_text = self.theme.description or "SDDM Greeter Theme"
        if len(desc_text) > 38:
            desc_text = desc_text[:35] + "..."
        self.desc_label = QLabel(desc_text)
        self.desc_label.setStyleSheet("font-size: 11px; color: #787c99;")
        layout.addWidget(self.desc_label)

    def _create_thumbnail(self) -> QPixmap:
        """Loads preview image or generates a stylish placeholder thumbnail."""
        target_size = QSize(204, 115)

        # Try theme preview or custom background
        img_path = self.theme.preview_path
        if not img_path and self.theme.custom_background:
            img_path = Path(self.theme.custom_background)
        if not img_path and self.theme.default_background:
            img_path = Path(self.theme.default_background)

        # Fallback inspection of files in theme directory
        if not img_path or not img_path.exists():
            for p in ["preview.png", "preview.jpg", "preview.jpeg", "preview.webp", "screenshot.png", "screenshot.jpg"]:
                cand = self.theme.path / p
                if cand.exists():
                    img_path = cand
                    break
        if not img_path or not img_path.exists():
            for p in [f"{self.theme.id}.jpg", f"{self.theme.id}.png", "background.jpg", "background.png", "images/background.png", "images/background.jpg"]:
                cand = self.theme.path / p
                if cand.exists():
                    img_path = cand
                    break

        if img_path and img_path.exists():
            try:
                pix = QPixmap(str(img_path))
                if not pix.isNull():
                    return pix.scaled(target_size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation).copy(
                        QRect(0, 0, target_size.width(), target_size.height())
                    )
            except Exception:
                pass

        # Generate styled placeholder pixmap
        pixmap = QPixmap(target_size)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Dark gradient background
        gradient = QLinearGradient(0, 0, target_size.width(), target_size.height())
        gradient.setColorAt(0.0, QColor(36, 40, 59))
        gradient.setColorAt(1.0, QColor(26, 27, 38))
        painter.fillRect(QRect(0, 0, target_size.width(), target_size.height()), gradient)

        # Draw decorative display outline
        painter.setPen(QPen(QColor(65, 72, 104), 1.5))
        rect_inner = QRect(20, 15, target_size.width() - 40, target_size.height() - 35)
        painter.drawRoundedRect(rect_inner, 6, 6)

        # Draw subtle login box silhouette
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(122, 162, 247, 40))
        login_box = QRect(50, 40, target_size.width() - 100, 30)
        painter.drawRoundedRect(login_box, 4, 4)

        # Theme Name text in placeholder
        painter.setPen(QColor(192, 202, 245))
        font = QFont("sans-serif", 10, QFont.Bold)
        painter.setFont(font)
        painter.drawText(QRect(0, 40, target_size.width(), 30), Qt.AlignCenter, self.theme.name[:20])

        painter.setPen(QColor(122, 162, 247))
        font_sub = QFont("sans-serif", 9)
        painter.setFont(font_sub)
        painter.drawText(QRect(0, 75, target_size.width(), 20), Qt.AlignCenter, f"SDDM {self.theme.display_qt_version}")

        painter.end()
        return pixmap

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self._update_style()

    def _update_style(self):
        if self.is_selected:
            self.setStyleSheet(
                "QFrame#themeCard { background-color: #24283b; border: 2px solid #7aa2f7; border-radius: 8px; }"
            )
        elif self.theme.is_active:
            self.setStyleSheet(
                "QFrame#themeCard { background-color: #1f2335; border: 1.5px solid #10b981; border-radius: 8px; }"
                "QFrame#themeCard:hover { background-color: #24283b; border-color: #34d399; }"
            )
        else:
            self.setStyleSheet(
                "QFrame#themeCard { background-color: #1f2335; border: 1px solid #292e42; border-radius: 8px; }"
                "QFrame#themeCard:hover { background-color: #24283b; border-color: #3b4261; }"
            )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.theme)
        elif event.button() == Qt.RightButton:
            self.context_menu_requested.emit(self.theme, event.globalPosition().toPoint())
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit(self.theme)
        super().mouseDoubleClickEvent(event)


class ThemeGridWidget(QWidget):
    """Container managing the scrollable grid of theme cards with search, filter, and sort."""

    theme_selected = Signal(object)  # Theme
    theme_double_clicked = Signal(object)  # Theme
    apply_requested = Signal(object)  # Theme
    sync_requested = Signal(object)  # Theme
    preview_requested = Signal(object)  # Theme
    set_background_requested = Signal(object)  # Theme
    reset_background_requested = Signal(object)  # Theme
    remove_requested = Signal(object)  # Theme
    open_folder_requested = Signal(object)  # Theme
    edit_requested = Signal(object)  # Theme
    equip_requested = Signal(object)  # Theme

    def __init__(self, parent=None):
        super().__init__(parent)
        self.themes: List[Theme] = []
        self.filtered_themes: List[Theme] = []
        self.cards: List[ThemeCard] = []
        self.selected_theme: Optional[Theme] = None

        self.search_text = ""
        self.qt_filter = "All"
        self.sort_by = "Name (A-Z)"

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(16, 16, 16, 16)
        self.grid_layout.setSpacing(14)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.scroll_area.setWidget(self.grid_container)
        main_layout.addWidget(self.scroll_area)

    def set_themes(self, themes: List[Theme]):
        """Sets full list of themes and applies current filter/sort."""
        self.themes = themes
        self.apply_filter_and_sort()

    def set_search_query(self, query: str):
        self.search_text = query.strip().lower()
        self.apply_filter_and_sort()

    def set_qt_filter(self, qt_filter: str):
        self.qt_filter = qt_filter
        self.apply_filter_and_sort()

    def set_sort_order(self, sort_by: str):
        self.sort_by = sort_by
        self.apply_filter_and_sort()

    def apply_filter_and_sort(self):
        """Filters and sorts themes, then rebuilds the grid cards."""
        # 1. Filter
        filtered = []
        for t in self.themes:
            # Search query
            if self.search_text:
                q = self.search_text
                match_name = q in t.name.lower()
                match_id = q in t.id.lower()
                match_desc = q in (t.description or "").lower()
                if not (match_name or match_id or match_desc):
                    continue

            # Qt Version filter
            if self.qt_filter == "Qt 6" and t.qt_version != "6":
                continue
            elif self.qt_filter == "Qt 5" and t.qt_version != "5":
                continue

            filtered.append(t)

        # 2. Sort
        if self.sort_by == "Name (A-Z)":
            filtered.sort(key=lambda x: x.name.lower())
        elif self.sort_by == "Name (Z-A)":
            filtered.sort(key=lambda x: x.name.lower(), reverse=True)
        elif self.sort_by == "Installation Date (Newest)":
            filtered.sort(key=lambda x: x.mtime, reverse=True)
        elif self.sort_by == "Installation Date (Oldest)":
            filtered.sort(key=lambda x: x.mtime)

        self.filtered_themes = filtered
        self._rebuild_grid()

    def _rebuild_grid(self):
        """Clears and repopulates the grid layout."""
        # Clear existing items
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.cards.clear()

        # If empty
        if not self.filtered_themes:
            empty_label = QLabel("No SDDM themes found matching the current filters.")
            empty_label.setStyleSheet("color: #787c99; font-size: 14px; padding: 40px;")
            empty_label.setAlignment(Qt.AlignCenter)
            self.grid_layout.addWidget(empty_label, 0, 0, 1, 3)
            return

        columns = 3  # responsive 3-column layout
        row = 0
        col = 0

        target_select_theme = None

        for theme in self.filtered_themes:
            card = ThemeCard(theme)
            card.clicked.connect(self._on_card_clicked)
            card.double_clicked.connect(self._on_card_double_clicked)
            card.context_menu_requested.connect(self._on_card_context_menu)

            # Preserve selection
            if self.selected_theme and self.selected_theme.path == theme.path:
                card.set_selected(True)
                target_select_theme = theme
            elif not target_select_theme and (theme.is_active or not self.selected_theme):
                target_select_theme = theme

            self.cards.append(card)
            self.grid_layout.addWidget(card, row, col)

            col += 1
            if col >= columns:
                col = 0
                row += 1

        # Select target theme if current selection is invalid
        if target_select_theme:
            self.select_theme(target_select_theme)

    def select_theme(self, theme: Theme):
        """Highlights the selected card and emits theme_selected."""
        self.selected_theme = theme
        for card in self.cards:
            is_match = card.theme.path == theme.path
            card.set_selected(is_match)
        self.theme_selected.emit(theme)

    def _on_card_clicked(self, theme: Theme):
        self.select_theme(theme)

    def _on_card_double_clicked(self, theme: Theme):
        self.theme_double_clicked.emit(theme)

    def _on_card_context_menu(self, theme: Theme, pos: QPoint):
        self.select_theme(theme)

        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background-color: #1f2335; color: #c0caf5; border: 1px solid #3b4261; border-radius: 6px; padding: 4px; }"
            "QMenu::item { padding: 6px 20px; border-radius: 4px; }"
            "QMenu::item:selected { background-color: #3b4261; color: #ffffff; }"
            "QMenu::separator { height: 1px; background-color: #292e42; margin: 4px 8px; }"
        )

        act_preview = menu.addAction("Preview Theme")
        if theme.is_active:
            act_apply = menu.addAction("Re-apply / Resync Theme")
        else:
            act_apply = menu.addAction("Apply Theme")

        act_sync = None
        if not theme.is_system:
            act_sync = menu.addAction("Sync to SDDM System Directory")

        menu.addSeparator()
        act_equip = menu.addAction("⚡ Equip Next-Gen Features…")
        act_edit = menu.addAction("✏️ Edit Theme (theme.conf & files)…")
        act_bg = menu.addAction("Set Background...")
        act_reset_bg = menu.addAction("Reset to Theme Default BG")
        menu.addSeparator()
        act_folder = menu.addAction("Open Theme Directory")
        menu.addSeparator()
        act_remove = menu.addAction("Remove Theme")

        action = menu.exec(pos)
        if action == act_preview:
            self.preview_requested.emit(theme)
        elif action == act_apply:
            self.apply_requested.emit(theme)
        elif act_sync and action == act_sync:
            self.sync_requested.emit(theme)
        elif action == act_equip:
            self.equip_requested.emit(theme)
        elif action == act_edit:
            self.edit_requested.emit(theme)
        elif action == act_bg:
            self.set_background_requested.emit(theme)
        elif action == act_reset_bg:
            self.reset_background_requested.emit(theme)
        elif action == act_folder:
            self.open_folder_requested.emit(theme)
        elif action == act_remove:
            self.remove_requested.emit(theme)
