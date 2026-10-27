"""
SDDM Theme Manager - Decentralized Marketplace & Rice-Drop Hub Dialog (Feature 19)
Community theme catalog with name search, tag filters, ratings, and theme bundle publisher.
"""

from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core.marketplace import DecentralizedMarketplace, MarketThemeItem


class MarketplaceDialog(QDialog):
    """Community Decentralized Theme Hub Modal."""

    theme_installed = Signal(Path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🌐 Rice-Drop Community Theme Hub")
        self.resize(580, 520)
        self.setMinimumWidth(480)
        self._setup_ui()
        self.load_themes()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        # Header Card
        header = QFrame()
        header.setStyleSheet("background-color: #1a1b26; border-radius: 8px; padding: 12px;")
        h_layout = QVBoxLayout(header)
        title = QLabel("🌐 Rice-Drop Community Theme Hub")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #7aa2f7;")
        h_layout.addWidget(title)

        desc = QLabel(
            "Discover, share, and install curated SDDM greeter themes built by Linux ricers and artists. "
            "Filter by aesthetic style tags or package your own theme for community sharing."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #9aa5ce; font-size: 12px;")
        h_layout.addWidget(desc)
        layout.addWidget(header)

        # Search & Filter Row
        filter_row = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Search themes by name or author…")
        self.txt_search.textChanged.connect(self.load_themes)
        filter_row.addWidget(self.txt_search)

        self.combo_tags = QComboBox()
        self.combo_tags.addItem("All Styles", "")
        self.combo_tags.addItem("Cyberpunk", "cyberpunk")
        self.combo_tags.addItem("Pastel", "pastel")
        self.combo_tags.addItem("Minimal", "minimal")
        self.combo_tags.addItem("Anime", "anime")
        self.combo_tags.addItem("Nordic", "nordic")
        self.combo_tags.currentIndexChanged.connect(self.load_themes)
        filter_row.addWidget(self.combo_tags)

        layout.addLayout(filter_row)

        # Themes List
        self.list_themes = QListWidget()
        self.list_themes.setStyleSheet(
            "QListWidget { background-color: #16161e; border: 1px solid #292e42; border-radius: 8px; padding: 6px; font-size: 12px; }"
            "QListWidget::item { padding: 10px; border-radius: 6px; margin-bottom: 6px; background-color: #1f2335; }"
            "QListWidget::item:selected { background-color: #283457; border: 1px solid #7aa2f7; }"
        )
        layout.addWidget(self.list_themes)

        # Actions
        btn_row = QHBoxLayout()
        self.btn_publish = QPushButton("📦 Package Local Theme for Publish…")
        self.btn_publish.setStyleSheet("color: #bb9af7;")
        self.btn_publish.clicked.connect(self._on_publish_clicked)
        btn_row.addWidget(self.btn_publish)

        btn_row.addStretch()

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def load_themes(self):
        query = self.txt_search.text().strip()
        tag = self.combo_tags.currentData() or None

        self.list_themes.clear()
        results = DecentralizedMarketplace.search_catalog(query=query, tag=tag)
        for item in results:
            tag_str = ", ".join(item.tags)
            text = f"🎨 {item.name} v{item.version} by {item.author}\n   {item.description}\n   Tags: [{tag_str}]  |  ⭐ {item.stars} stars  |  ⬇ {item.downloads} downloads"
            w_item = QListWidgetItem(text)
            w_item.setData(Qt.UserRole, item)
            self.list_themes.addItem(w_item)

    def _on_publish_clicked(self):
        theme_dir = QFileDialog.getExistingDirectory(self, "Select Theme Directory to Package")
        if not theme_dir:
            return

        out_tar, _ = QFileDialog.getSaveFileName(self, "Save Theme Package Bundle", f"{Path(theme_dir).name}.tar.gz", "Tar Gzip (*.tar.gz)")
        if not out_tar:
            return

        ok, msg = DecentralizedMarketplace.package_theme_for_publish(Path(theme_dir), Path(out_tar))
        if ok:
            QMessageBox.information(self, "Theme Packaged", f"🎉 {msg}")
        else:
            QMessageBox.warning(self, "Packaging Error", f"Could not package theme: {msg}")
