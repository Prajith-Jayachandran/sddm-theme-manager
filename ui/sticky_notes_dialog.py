"""
SDDM Theme Manager - Sticky Notes & Household Bulletin Dialog (Feature 12)
Interactive manager to compose, color-code, edit, and delete notes rendered on the SDDM greeter.
"""

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from core.live_daemon import LiveTelemetryDaemon
from core.sticky_notes import StickyNote, StickyNotesManager


class StickyNotesDialog(QDialog):
    """Manage pre-login household sticky notes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📝 Household Sticky Notes Bulletin")
        self.resize(520, 480)
        self.setMinimumWidth(440)
        self._setup_ui()
        self.refresh_notes_list()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        # Header Card
        header = QFrame()
        header.setStyleSheet("background-color: #1a1b26; border-radius: 8px; padding: 12px;")
        h_layout = QVBoxLayout(header)
        title = QLabel("📝 Household Pre-Login Notes")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #7aa2f7;")
        h_layout.addWidget(title)

        desc = QLabel(
            "Leave memos, reminders, or maintenance notices for users before they log in. "
            "Notes appear as interactive floating memo cards on the SDDM login screen."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #9aa5ce; font-size: 12px;")
        h_layout.addWidget(desc)
        layout.addWidget(header)

        # Main List
        lbl_list = QLabel("Active Household Notes:")
        lbl_list.setStyleSheet("font-weight: bold; color: #c0caf5;")
        layout.addWidget(lbl_list)

        self.list_notes = QListWidget()
        self.list_notes.setStyleSheet(
            "QListWidget { background-color: #16161e; border: 1px solid #292e42; border-radius: 6px; padding: 6px; font-size: 12px; }"
            "QListWidget::item { padding: 8px; border-radius: 4px; margin-bottom: 4px; }"
            "QListWidget::item:selected { background-color: #283457; color: #7aa2f7; }"
        )
        layout.addWidget(self.list_notes)

        # Note Editor Group
        editor_frame = QFrame()
        editor_frame.setStyleSheet("background-color: #1a1b26; border-radius: 8px; padding: 10px;")
        e_layout = QVBoxLayout(editor_frame)
        e_layout.setSpacing(8)

        # Title & Author Row
        row1 = QHBoxLayout()
        self.txt_title = QLineEdit()
        self.txt_title.setPlaceholderText("Note Title (e.g. Rendering in Progress)")
        row1.addWidget(self.txt_title)

        self.txt_author = QLineEdit()
        self.txt_author.setPlaceholderText("Author (e.g. Prajith)")
        self.txt_author.setFixedWidth(140)
        row1.addWidget(self.txt_author)
        e_layout.addLayout(row1)

        # Content
        self.txt_content = QTextEdit()
        self.txt_content.setPlaceholderText("Message body (e.g. Do not shut down or reboot, Blender rendering 4K frame sequence...)")
        self.txt_content.setMaximumHeight(70)
        e_layout.addWidget(self.txt_content)

        # Color & Add Row
        row2 = QHBoxLayout()
        lbl_col = QLabel("Note Color:")
        lbl_col.setStyleSheet("color: #9aa5ce; font-size: 11px;")
        row2.addWidget(lbl_col)

        self.combo_color = QComboBox()
        for cname, chex in StickyNotesManager.NOTE_COLORS.items():
            self.combo_color.addItem(cname.capitalize(), chex)
        row2.addWidget(self.combo_color)

        row2.addStretch()

        self.btn_add = QPushButton("➕ Post Note to Greeter")
        self.btn_add.setStyleSheet(
            "QPushButton { background-color: #7aa2f7; color: #1a1b26; font-weight: bold; padding: 6px 14px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #89b4fa; }"
        )
        self.btn_add.clicked.connect(self._on_add_clicked)
        row2.addWidget(self.btn_add)
        e_layout.addLayout(row2)

        layout.addWidget(editor_frame)

        # Actions
        btn_row = QHBoxLayout()
        self.btn_delete = QPushButton("🗑️ Delete Selected")
        self.btn_delete.setStyleSheet("color: #f7768e;")
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        btn_row.addWidget(self.btn_delete)

        btn_row.addStretch()

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def refresh_notes_list(self):
        self.list_notes.clear()
        notes = StickyNotesManager.load_notes()
        for n in notes:
            item = QListWidgetItem(f"📌 {n.title} — {n.author}: \"{n.content}\"")
            item.setData(Qt.UserRole, n.note_id)
            self.list_notes.addItem(item)
        self.btn_delete.setEnabled(len(notes) > 0)

    def _on_add_clicked(self):
        title = self.txt_title.text().strip()
        content = self.txt_content.toPlainText().strip()
        author = self.txt_author.text().strip() or "User"
        color = self.combo_color.currentData() or "#fef08a"

        if not title or not content:
            QMessageBox.warning(self, "Incomplete Note", "Please enter both a title and message body.")
            return

        StickyNotesManager.add_note(title=title, content=content, author=author, color=color)
        LiveTelemetryDaemon.update_notes()
        self.txt_title.clear()
        self.txt_content.clear()
        self.refresh_notes_list()
        QMessageBox.information(self, "Note Posted", "✅ Note posted to SDDM greeter bulletin successfully!")

    def _on_delete_clicked(self):
        item = self.list_notes.currentItem()
        if not item:
            return
        note_id = item.data(Qt.UserRole)
        StickyNotesManager.delete_note(note_id)
        LiveTelemetryDaemon.update_notes()
        self.refresh_notes_list()
