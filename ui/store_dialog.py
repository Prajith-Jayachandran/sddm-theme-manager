"""
SDDM Theme Manager - KDE Store Browser Dialog
Allows browsing, searching, and 1-click installing themes from the KDE Store / Pling API.
"""

import urllib.request
from typing import List, Optional

from PySide6.QtCore import QSize, Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.store_client import StoreClient, StoreItem


class ThumbnailLoaderThread(QThread):
    loaded = Signal(bytes)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            req = urllib.request.Request(self.url, headers={"User-Agent": "SDDM-Theme-Manager/1.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = resp.read()
                self.loaded.emit(data)
        except Exception:
            pass


class FetchThemesThread(QThread):
    themes_fetched = Signal(bool, list, str)

    def __init__(self, search: str = "", sort_by: str = "latest"):
        super().__init__()
        self.search = search
        self.sort_by = sort_by

    def run(self):
        ok, items, msg = StoreClient.fetch_themes(page=1, page_size=20, search_query=self.search, sort_by=self.sort_by)
        self.themes_fetched.emit(ok, items, msg)


class DownloadThemeThread(QThread):
    progress = Signal(int, int)
    finished = Signal(bool, str)

    def __init__(self, item: StoreItem):
        super().__init__()
        self.item = item

    def run(self):
        def on_prog(downloaded, total):
            self.progress.emit(downloaded, total)

        ok, path, msg = StoreClient.download_and_install(self.item, progress_callback=on_prog)
        self.finished.emit(ok, msg)


class StoreItemWidget(QFrame):
    install_requested = Signal(object)  # StoreItem

    def __init__(self, item: StoreItem, parent=None):
        super().__init__(parent)
        self.item = item
        self.thumb_thread: Optional[ThumbnailLoaderThread] = None
        self.setStyleSheet(
            "QFrame { background-color: #1f2335; border: 1px solid #292e42; border-radius: 6px; padding: 10px; }"
            "QFrame:hover { border-color: #3b4261; background-color: #24283b; }"
        )
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(14)

        # 1. Thumbnail Container (110x65)
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(110, 65)
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setStyleSheet("background-color: #16161e; border-radius: 4px; border: 1px solid #292e42;")
        self._set_placeholder_thumb()

        if self.item.preview_url:
            self.thumb_thread = ThumbnailLoaderThread(self.item.preview_url)
            self.thumb_thread.loaded.connect(self._on_thumb_loaded)
            self.thumb_thread.start()

        layout.addWidget(self.thumb_label)

        # 2. Info column
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        title_lbl = QLabel(self.item.name)
        title_lbl.setStyleSheet("font-weight: 600; font-size: 14px; color: #ffffff;")
        info_layout.addWidget(title_lbl)

        meta_text = f"By {self.item.author}  |  Downloads: {self.item.downloads}  |  Score: {self.item.score}%"
        meta_lbl = QLabel(meta_text)
        meta_lbl.setStyleSheet("font-size: 11px; color: #787c99;")
        info_layout.addWidget(meta_lbl)

        desc_snippet = self.item.description[:120] + "..." if len(self.item.description) > 120 else self.item.description
        if not desc_snippet.strip():
            desc_snippet = "No description available."
        desc_lbl = QLabel(desc_snippet)
        desc_lbl.setStyleSheet("font-size: 11px; color: #9aa5ce;")
        desc_lbl.setWordWrap(True)
        info_layout.addWidget(desc_lbl)

        layout.addLayout(info_layout, 1)

        # 3. Install button
        self.btn_install = QPushButton("Download & Install")
        self.btn_install.setStyleSheet(
            "background-color: #3d59a1; color: #ffffff; border: 1px solid #7aa2f7; font-weight: 600; padding: 6px 12px; border-radius: 4px;"
        )
        self.btn_install.setCursor(Qt.PointingHandCursor)
        self.btn_install.clicked.connect(lambda: self.install_requested.emit(self.item))
        layout.addWidget(self.btn_install)

    def _set_placeholder_thumb(self):
        pixmap = QPixmap(110, 65)
        pixmap.fill(QColor(22, 22, 30))
        self.thumb_label.setPixmap(pixmap)

    def _on_thumb_loaded(self, data: bytes):
        pix = QPixmap()
        if pix.loadFromData(data) and not pix.isNull():
            scaled = pix.scaled(110, 65, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation).copy(0, 0, 110, 65)
            self.thumb_label.setPixmap(scaled)

    def stop_threads(self):
        if self.thumb_thread and self.thumb_thread.isRunning():
            self.thumb_thread.terminate()
            self.thumb_thread.wait(500)


class StoreDialog(QDialog):
    theme_installed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Get New SDDM Themes - KDE Store")
        self.resize(750, 550)
        self.setStyleSheet("background-color: #1a1b26; color: #c0caf5;")

        self.fetch_thread: Optional[FetchThemesThread] = None
        self.download_thread: Optional[DownloadThemeThread] = None

        self._init_ui()
        self._load_themes()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Top Bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search online SDDM themes...")
        self.search_input.returnPressed.connect(self._load_themes)
        top_bar.addWidget(self.search_input, 1)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Latest (Newest)", "High Rating", "Most Downloaded"])
        self.sort_combo.currentIndexChanged.connect(self._load_themes)
        top_bar.addWidget(self.sort_combo)

        btn_search = QPushButton("Search")
        btn_search.clicked.connect(self._load_themes)
        top_bar.addWidget(btn_search)

        main_layout.addLayout(top_bar)

        # Progress / Status
        self.status_bar = QHBoxLayout()
        self.lbl_status = QLabel("Connecting to KDE Store...")
        self.lbl_status.setStyleSheet("color: #7aa2f7; font-size: 11px;")
        self.status_bar.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        self.status_bar.addWidget(self.progress_bar)

        main_layout.addLayout(self.status_bar)

        # Scroll Area for themes
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

        self.items_container = QWidget()
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(8)
        self.items_layout.setAlignment(Qt.AlignTop)

        self.scroll_area.setWidget(self.items_container)
        main_layout.addWidget(self.scroll_area, 1)

        # Bottom Close button
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        bottom_layout.addWidget(btn_close)
        main_layout.addLayout(bottom_layout)

    def _cleanup_threads(self):
        if self.fetch_thread and self.fetch_thread.isRunning():
            self.fetch_thread.requestInterruption()
            self.fetch_thread.quit()
            if not self.fetch_thread.wait(150):
                self.fetch_thread.terminate()
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.requestInterruption()
            self.download_thread.quit()
            if not self.download_thread.wait(150):
                self.download_thread.terminate()
        # Clean up item widgets' thumbnail threads
        for i in range(self.items_layout.count()):
            item = self.items_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), StoreItemWidget):
                item.widget().stop_threads()

    def closeEvent(self, event):
        self._cleanup_threads()
        super().closeEvent(event)

    def reject(self):
        self._cleanup_threads()
        super().reject()

    def accept(self):
        self._cleanup_threads()
        super().accept()

    def _load_themes(self):
        query = self.search_input.text()
        sort_map = {0: "latest", 1: "high", 2: "down"}
        sort_mode = sort_map.get(self.sort_combo.currentIndex(), "latest")

        self.lbl_status.setText("Fetching themes from KDE Store...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # indeterminate

        # Clear items
        while self.items_layout.count():
            item = self.items_layout.takeAt(0)
            if item.widget():
                if isinstance(item.widget(), StoreItemWidget):
                    item.widget().stop_threads()
                item.widget().deleteLater()

        self.fetch_thread = FetchThemesThread(query, sort_mode)
        self.fetch_thread.themes_fetched.connect(self._on_themes_fetched)
        self.fetch_thread.start()

    def _on_themes_fetched(self, ok: bool, items: List[StoreItem], msg: str):
        self.progress_bar.setVisible(False)
        if not ok:
            self.lbl_status.setText(f"Error: {msg}")
            lbl_err = QLabel(f"Unable to load themes:\n{msg}")
            lbl_err.setStyleSheet("color: #f7768e; padding: 20px;")
            lbl_err.setAlignment(Qt.AlignCenter)
            self.items_layout.addWidget(lbl_err)
            return

        self.lbl_status.setText(f"Found {len(items)} themes.")
        if not items:
            lbl_none = QLabel("No themes found for this query.")
            lbl_none.setStyleSheet("color: #787c99; padding: 20px;")
            lbl_none.setAlignment(Qt.AlignCenter)
            self.items_layout.addWidget(lbl_none)
            return

        for item in items:
            w = StoreItemWidget(item)
            w.install_requested.connect(self._on_install_item)
            self.items_layout.addWidget(w)

    def _on_install_item(self, item: StoreItem):
        self.lbl_status.setText(f"Downloading and installing '{item.name}'...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.download_thread = DownloadThemeThread(item)
        self.download_thread.progress.connect(self._on_download_progress)
        self.download_thread.finished.connect(self._on_download_finished)
        self.download_thread.start()

    def _on_download_progress(self, downloaded: int, total: int):
        if total > 0:
            pct = int((downloaded / total) * 100)
            self.progress_bar.setValue(pct)
            self.lbl_status.setText(f"Downloading... ({pct}%)")

    def _on_download_finished(self, ok: bool, msg: str):
        self.progress_bar.setVisible(False)
        if ok:
            self.lbl_status.setText(f"Success: {msg}")
            self.theme_installed.emit()
        else:
            self.lbl_status.setText(f"Installation failed: {msg}")
