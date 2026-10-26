"""
SDDM Theme Manager - Theme Editor Dialog
Full-featured code and configuration editor for SDDM themes.
Allows viewing and editing theme.conf, metadata.desktop, Main.qml, and all other files
with syntax highlighting, line numbers, live background preview, and polkit integration.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set

from PySide6.QtCore import QPoint, QRect, QRegularExpression, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QFontDatabase,
    QIcon,
    QKeySequence,
    QPainter,
    QPixmap,
    QShortcut,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.polkit import write_file_privileged
from core.theme_applier import ThemeApplier
from ui.theme_writer import ThemeWriter

TEXT_EXTENSIONS = {
    ".conf",
    ".user",
    ".orig",
    ".desktop",
    ".json",
    ".qml",
    ".js",
    ".txt",
    ".sh",
    ".xml",
    ".css",
    ".qss",
    ".ini",
    ".md",
    ".frag",
    ".vert",
    ".glsl",
}


class INISyntaxHighlighter(QSyntaxHighlighter):
    """
    Syntax highlighter for SDDM theme.conf and .desktop INI files.
    - [Section] : #89b4fa, bold
    - key       : #a6e3a1, normal
    - =         : #f9e2af, normal
    - value     : #cdd6f4, normal
    - # comment : #6c7086, italic
    - Empty val : #f38ba8, underline
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#6c7086"))
        self.comment_format.setFontItalic(True)

        self.section_format = QTextCharFormat()
        self.section_format.setForeground(QColor("#89b4fa"))
        self.section_format.setFontWeight(QFont.Bold)

        self.key_format = QTextCharFormat()
        self.key_format.setForeground(QColor("#a6e3a1"))

        self.operator_format = QTextCharFormat()
        self.operator_format.setForeground(QColor("#f9e2af"))

        self.value_format = QTextCharFormat()
        self.value_format.setForeground(QColor("#cdd6f4"))

        self.empty_val_format = QTextCharFormat()
        self.empty_val_format.setForeground(QColor("#f38ba8"))
        self.empty_val_format.setFontUnderline(True)

    def highlightBlock(self, text: str):
        stripped = text.strip()

        # Comments
        if stripped.startswith("#") or stripped.startswith(";"):
            self.setFormat(0, len(text), self.comment_format)
            return

        # Section headers: [Section]
        if stripped.startswith("[") and "]" in stripped:
            start_idx = text.find("[")
            end_idx = text.rfind("]")
            if end_idx > start_idx:
                self.setFormat(start_idx, end_idx - start_idx + 1, self.section_format)
                comment_idx = text.find("#", end_idx)
                if comment_idx != -1:
                    self.setFormat(comment_idx, len(text) - comment_idx, self.comment_format)
                return

        # Key = Value pairs
        eq_idx = text.find("=")
        if eq_idx != -1:
            self.setFormat(0, eq_idx, self.key_format)
            self.setFormat(eq_idx, 1, self.operator_format)

            val_text = text[eq_idx + 1 :]
            val_start = eq_idx + 1

            inline_comment_idx = -1
            in_quote = False
            for i, ch in enumerate(val_text):
                if ch in ('"', "'"):
                    in_quote = not in_quote
                elif ch in ("#", ";") and not in_quote:
                    inline_comment_idx = i
                    break

            if inline_comment_idx != -1:
                actual_val = val_text[:inline_comment_idx]
                comment_part = val_text[inline_comment_idx:]
                if not actual_val.strip():
                    self.setFormat(val_start, len(actual_val), self.empty_val_format)
                else:
                    self.setFormat(val_start, len(actual_val), self.value_format)
                self.setFormat(val_start + inline_comment_idx, len(comment_part), self.comment_format)
            else:
                if not val_text.strip():
                    self.setFormat(val_start, max(1, len(val_text)), self.empty_val_format)
                else:
                    self.setFormat(val_start, len(val_text), self.value_format)


class QMLSyntaxHighlighter(QSyntaxHighlighter):
    """
    Syntax highlighter for QML, JavaScript, and JSON files in SDDM themes.
    - Keywords: #cba6f7 (purple), bold
    - QML Types: #89b4fa (blue), bold
    - Strings: #a6e3a1 (green)
    - Numbers: #fab387 (orange)
    - Comments: #6c7086 (italic)
    - Properties: #89dceb (cyan)
    """

    KEYWORDS = [
        r"\bimport\b", r"\bproperty\b", r"\breadonly\b", r"\balias\b", r"\bsignal\b",
        r"\bfunction\b", r"\bid\b", r"\bas\b", r"\bvar\b", r"\blet\b", r"\bconst\b",
        r"\breturn\b", r"\bif\b", r"\belse\b", r"\bfor\b", r"\bwhile\b", r"\bdo\b",
        r"\bswitch\b", r"\bcase\b", r"\bbreak\b", r"\bcontinue\b", r"\bnew\b",
        r"\bthis\b", r"\btypeof\b", r"\binstanceof\b", r"\btry\b", r"\bcatch\b",
        r"\bfinally\b", r"\bthrow\b", r"\btrue\b", r"\bfalse\b", r"\bnull\b", r"\bundefined\b"
    ]

    COMPONENTS = [
        r"\bItem\b", r"\bRectangle\b", r"\bText\b", r"\bImage\b", r"\bMouseArea\b",
        r"\bFocusScope\b", r"\bComponent\b", r"\bLoader\b", r"\bRepeater\b",
        r"\bRow\b", r"\bColumn\b", r"\bGrid\b", r"\bFlow\b", r"\bLayout\b",
        r"\bRowLayout\b", r"\bColumnLayout\b", r"\bGridLayout\b", r"\bStackLayout\b",
        r"\bTimer\b", r"\bConnections\b", r"\bBinding\b", r"\bPropertyAnimation\b",
        r"\bNumberAnimation\b", r"\bColorAnimation\b", r"\bSequentialAnimation\b",
        r"\bParallelAnimation\b", r"\bFontLoader\b", r"\bDropShadow\b", r"\bFastBlur\b",
        r"\bColorOverlay\b", r"\bMediaPlayer\b", r"\bVideoOutput\b", r"\bTextEdit\b",
        r"\bTextInput\b", r"\bButton\b", r"\bTextField\b", r"\bComboBox\b",
        r"\bCheckBox\b", r"\bProgressBar\b", r"\bSlider\b", r"\bScrollView\b",
        r"\bListView\b", r"\bGridView\b", r"\bPathView\b", r"\bint\b", r"\bstring\b",
        r"\bbool\b", r"\breal\b", r"\bdouble\b", r"\bcolor\b", r"\burl\b"
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rules = []

        # Keywords format
        kw_fmt = QTextCharFormat()
        kw_fmt.setForeground(QColor("#cba6f7"))
        kw_fmt.setFontWeight(QFont.Bold)
        for pattern in self.KEYWORDS:
            self.rules.append((re.compile(pattern), kw_fmt))

        # Components format
        comp_fmt = QTextCharFormat()
        comp_fmt.setForeground(QColor("#89b4fa"))
        comp_fmt.setFontWeight(QFont.Bold)
        for pattern in self.COMPONENTS:
            self.rules.append((re.compile(pattern), comp_fmt))

        # Property assignment format (e.g. width: or color:)
        prop_fmt = QTextCharFormat()
        prop_fmt.setForeground(QColor("#89dceb"))
        self.rules.append((re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*\s*(?=:)"), prop_fmt))

        # Numbers format
        num_fmt = QTextCharFormat()
        num_fmt.setForeground(QColor("#fab387"))
        self.rules.append((re.compile(r"\b[0-9]+(\.[0-9]+)?\b"), num_fmt))

        # String format
        str_fmt = QTextCharFormat()
        str_fmt.setForeground(QColor("#a6e3a1"))
        self.rules.append((re.compile(r'"[^"\\]*(\\.[^"\\]*)*"'), str_fmt))
        self.rules.append((re.compile(r"'[^'\\]*(\\.[^'\\]*)*'"), str_fmt))

        # Single-line comments
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#6c7086"))
        self.comment_format.setFontItalic(True)
        self.rules.append((re.compile(r"//[^\n]*"), self.comment_format))

    def highlightBlock(self, text: str):
        # 1. Single-line pattern rules
        for pattern, fmt in self.rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)

        # 2. Multi-line comments /* ... */
        self.setCurrentBlockState(0)
        start_index = 0
        if self.previousBlockState() != 1:
            start_index = text.find("/*")

        while start_index >= 0:
            end_index = text.find("*/", start_index + 2)
            if end_index == -1:
                self.setCurrentBlockState(1)
                comment_length = len(text) - start_index
            else:
                comment_length = end_index - start_index + 2
            self.setFormat(start_index, comment_length, self.comment_format)
            start_index = text.find("/*", start_index + comment_length)


class LineNumberArea(QWidget):
    """Custom line number gutter widget attached to CodeEditor."""

    def __init__(self, editor: "CodeEditor"):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    """Code editor QPlainTextEdit with line numbers, tab spacing, and escape sequence detection."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)
        self.invalid_escape_lines: Set[int] = set()
        self.enable_escape_warning = True
        self.comment_prefix = "# "

        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        for cand in ["JetBrains Mono", "Fira Code", "DejaVu Sans Mono", "monospace"]:
            if cand in QFontDatabase.families():
                font.setFamily(cand)
                break
        font.setPointSize(11)
        self.setFont(font)

        self.setStyleSheet(
            "QPlainTextEdit {"
            "  background-color: #1e1e2e;"
            "  color: #cdd6f4;"
            "  border: 1px solid #313244;"
            "  border-radius: 6px;"
            "  padding: 4px;"
            "  selection-background-color: #45475a;"
            "  selection-color: #cdd6f4;"
            "}"
        )

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.textChanged.connect(self.scan_escape_sequences)

        self.update_line_number_area_width(0)
        self.highlight_current_line()

    def line_number_area_width(self) -> int:
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        space = 24 + self.fontMetrics().horizontalAdvance("9") * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect: QRect, dy: int):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def highlight_current_line(self):
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor("#313244")
            line_color.setAlpha(60)
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextCharFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    def scan_escape_sequences(self):
        """Scans for unrecognized escape sequences and marks line numbers for warning icons."""
        self.invalid_escape_lines.clear()
        if not self.enable_escape_warning:
            self.line_number_area.update()
            return

        text = self.toPlainText()
        lines = text.split("\n")
        valid_escapes = {"n", "t", "r", "\\", "s", ";", "#", '"', "'", "x"}

        for idx, line in enumerate(lines):
            eq_idx = line.find("=")
            if eq_idx != -1:
                val = line[eq_idx + 1 :]
                i = 0
                while i < len(val):
                    if val[i] == "\\":
                        if i + 1 >= len(val):
                            self.invalid_escape_lines.add(idx + 1)
                            break
                        next_ch = val[i + 1]
                        if next_ch not in valid_escapes and not next_ch.isdigit():
                            self.invalid_escape_lines.add(idx + 1)
                            break
                        i += 1
                    i += 1
        self.line_number_area.update()

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#181825"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        painter.setFont(self.font())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                line_num = block_number + 1
                number_str = str(line_num)

                if line_num in self.invalid_escape_lines:
                    painter.drawText(2, top + self.fontMetrics().ascent(), "⚠️")

                painter.setPen(QColor("#6c7086"))
                painter.drawText(
                    0,
                    top,
                    self.line_number_area.width() - 8,
                    self.fontMetrics().height(),
                    Qt.AlignRight,
                    number_str,
                )

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Tab:
            self.insertPlainText("    ")
            return
        if event.key() == Qt.Key_Slash and event.modifiers() == Qt.ControlModifier:
            self.toggle_comment()
            return
        super().keyPressEvent(event)

    def toggle_comment(self):
        """Prepends or removes comment prefix on selected lines."""
        cursor = self.textCursor()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()

        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.StartOfLine)
        start_block = cursor.blockNumber()

        cursor.setPosition(end)
        cursor.movePosition(QTextCursor.EndOfLine)
        end_block = cursor.blockNumber()

        doc = self.document()
        cursor.beginEditBlock()

        prefix = self.comment_prefix
        clean_prefix = prefix.strip()

        for b_num in range(start_block, end_block + 1):
            block = doc.findBlockByNumber(b_num)
            text = block.text()
            b_cursor = QTextCursor(block)
            b_cursor.movePosition(QTextCursor.StartOfLine)

            if text.startswith(prefix):
                for _ in range(len(prefix)):
                    b_cursor.deleteChar()
            elif text.startswith(clean_prefix):
                for _ in range(len(clean_prefix)):
                    b_cursor.deleteChar()
            else:
                b_cursor.insertText(prefix)

        cursor.endEditBlock()


class ThemeEditor(QDialog):
    """
    Separate 900x620 dark Theme Editor modal dialog.
    Allows viewing and editing theme.conf, metadata.desktop, Main.qml, and all other files
    with debounced live preview, escape sequence parsing, and bottom toolbar.
    """

    theme_saved = Signal(Path)

    def __init__(self, theme_path: Path | str, parent=None, initial_file: Optional[str] = None):
        super().__init__(parent)
        self.theme_path = Path(theme_path).resolve()
        self.conf_path = self.theme_path / "theme.conf"
        self.active_file_path: Path = self.conf_path
        self.is_dirty = False
        self._initial_file_name = initial_file

        self.setWindowTitle(f"Edit: {self.theme_path.name}")
        self.resize(920, 640)
        self.setMinimumSize(820, 520)

        self.setStyleSheet(
            "QDialog {"
            "  background-color: #1a1b26;"
            "  color: #c0caf5;"
            "}"
            "QLabel {"
            "  color: #c0caf5;"
            "}"
            "QComboBox {"
            "  background-color: #24283b;"
            "  color: #c0caf5;"
            "  border: 1px solid #3b4261;"
            "  border-radius: 6px;"
            "  padding: 6px 10px;"
            "  font-size: 12px;"
            "}"
            "QComboBox:hover {"
            "  border-color: #7aa2f7;"
            "}"
            "QComboBox QAbstractItemView {"
            "  background-color: #1f2335;"
            "  color: #c0caf5;"
            "  selection-background-color: #3d59a1;"
            "  selection-color: #ffffff;"
            "  border: 1px solid #3b4261;"
            "}"
            "QPushButton, QToolButton {"
            "  background-color: #24283b;"
            "  color: #c0caf5;"
            "  border: 1px solid #3b4261;"
            "  border-radius: 6px;"
            "  padding: 6px 14px;"
            "  font-weight: 500;"
            "}"
            "QPushButton:hover, QToolButton:hover {"
            "  background-color: #2f354f;"
            "  border-color: #7aa2f7;"
            "  color: #ffffff;"
            "}"
            "QPushButton#saveApplyBtn {"
            "  background-color: #3d59a1;"
            "  color: #ffffff;"
            "  border: 1px solid #7aa2f7;"
            "  font-weight: 600;"
            "}"
            "QPushButton#saveApplyBtn:hover {"
            "  background-color: #7aa2f7;"
            "  color: #1a1b26;"
            "}"
        )

        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(300)
        self.preview_timer.timeout.connect(self.update_live_preview)

        self.ini_highlighter: Optional[INISyntaxHighlighter] = None
        self.qml_highlighter: Optional[QMLSyntaxHighlighter] = None

        self._build_ui()
        self.populate_files()
        self._setup_shortcuts()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Splitter (55% left, 45% right)
        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setStyleSheet("QSplitter::handle { background-color: #24283b; width: 4px; }")

        # Left panel: Code Editor with File Switcher
        left_widget = QWidget(self)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # File switcher row
        file_header_layout = QHBoxLayout()
        file_header_layout.setSpacing(8)

        lbl_file = QLabel("<b>Theme File:</b>", left_widget)
        file_header_layout.addWidget(lbl_file)

        self.combo_files = QComboBox(left_widget)
        self.combo_files.setCursor(Qt.PointingHandCursor)
        self.combo_files.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo_files.currentIndexChanged.connect(self._on_combo_file_changed)
        file_header_layout.addWidget(self.combo_files, 1)

        self.btn_new_file = QToolButton(left_widget)
        self.btn_new_file.setText("➕ New File…")
        self.btn_new_file.setToolTip("Create a new configuration or QML file in this theme")
        self.btn_new_file.clicked.connect(self._on_new_file_clicked)
        file_header_layout.addWidget(self.btn_new_file)

        self.btn_refresh_files = QToolButton(left_widget)
        self.btn_refresh_files.setText("🔄")
        self.btn_refresh_files.setToolTip("Refresh theme files list")
        self.btn_refresh_files.clicked.connect(self.populate_files)
        file_header_layout.addWidget(self.btn_refresh_files)

        left_layout.addLayout(file_header_layout)

        # Code Editor
        self.editor = CodeEditor(left_widget)
        self.editor.textChanged.connect(self._on_text_changed)
        left_layout.addWidget(self.editor, 1)

        splitter.addWidget(left_widget)

        # Right panel: Live Preview
        right_widget = QWidget(self)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        preview_header = QLabel("<b>Live Preview & Theme Context</b>", right_widget)
        right_layout.addWidget(preview_header)

        self.preview_container = QFrame(right_widget)
        self.preview_container.setStyleSheet(
            "QFrame {"
            "  background-color: #16161e;"
            "  border: 1px solid #3b4261;"
            "  border-radius: 8px;"
            "}"
        )
        container_layout = QVBoxLayout(self.preview_container)
        container_layout.setContentsMargins(8, 8, 8, 8)

        self.lbl_preview_image = QLabel(self.preview_container)
        self.lbl_preview_image.setAlignment(Qt.AlignCenter)
        self.lbl_preview_image.setStyleSheet("QLabel { background-color: transparent; }")
        self.lbl_preview_image.setMinimumSize(320, 200)
        container_layout.addWidget(self.lbl_preview_image, 1)

        # Metadata strip
        self.lbl_meta_strip = QLabel("type: image | Loading…", self.preview_container)
        self.lbl_meta_strip.setAlignment(Qt.AlignCenter)
        self.lbl_meta_strip.setStyleSheet(
            "QLabel {"
            "  color: #9aa5ce;"
            "  font-size: 11px;"
            "  padding: 4px;"
            "  background-color: #1f2335;"
            "  border-radius: 4px;"
            "}"
        )
        container_layout.addWidget(self.lbl_meta_strip)

        right_layout.addWidget(self.preview_container, 1)
        splitter.addWidget(right_widget)

        splitter.setSizes([520, 400])
        main_layout.addWidget(splitter, 1)

        # Bottom Toolbar
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(10)

        self.btn_save_apply = QPushButton("⚡ Save & Apply")
        self.btn_save_apply.setObjectName("saveApplyBtn")
        self.btn_save_apply.setToolTip("Save theme file and apply theme to SDDM")
        self.btn_save_apply.clicked.connect(self.save_and_apply)
        bottom_bar.addWidget(self.btn_save_apply)

        self.btn_save_file = QPushButton("💾 Save File")
        self.btn_save_file.setToolTip("Save current file (Ctrl+S)")
        self.btn_save_file.clicked.connect(self.save_current_file)
        bottom_bar.addWidget(self.btn_save_file)

        self.btn_choose_bg = QPushButton("🖼️ Choose Background…")
        self.btn_choose_bg.setToolTip("Select background image file (Ctrl+B)")
        self.btn_choose_bg.clicked.connect(self.choose_background)
        bottom_bar.addWidget(self.btn_choose_bg)

        bottom_bar.addStretch()

        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.close_with_check)
        bottom_bar.addWidget(self.btn_close)

        main_layout.addLayout(bottom_bar)

    def _setup_shortcuts(self):
        sc_save = QShortcut(QKeySequence("Ctrl+S"), self)
        sc_save.activated.connect(self.save_current_file)

        sc_bg = QShortcut(QKeySequence("Ctrl+B"), self)
        sc_bg.activated.connect(self.choose_background)

        sc_esc = QShortcut(QKeySequence("Escape"), self)
        sc_esc.activated.connect(self.close_with_check)

    def populate_files(self):
        """Scans theme directory recursively for all text/config files and populates file combo box."""
        if self.is_dirty:
            reply = QMessageBox.question(
                self,
                "Discard Changes?",
                f"You have unsaved changes in '{self.active_file_path.name}'. Refreshing will discard them. Proceed?",
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if reply != QMessageBox.StandardButton.Discard:
                return

        current_active = self.active_file_path.name if self.active_file_path else "theme.conf"
        self.combo_files.blockSignals(True)
        self.combo_files.clear()

        discovered_files: List[Path] = []
        if self.theme_path.exists():
            for root, dirs, files in os.walk(self.theme_path):
                # Avoid hidden directories (.git, .cache)
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for f in files:
                    p = Path(root) / f
                    if p.suffix.lower() in TEXT_EXTENSIONS or f in ("theme.conf", "theme.conf.user", "metadata.desktop"):
                        discovered_files.append(p)

        # Sort priority: theme.conf, theme.conf.user, metadata.desktop, metadata.json, Main.qml, then others
        def file_sort_key(p: Path):
            rel = p.relative_to(self.theme_path).as_posix()
            name_l = p.name.lower()
            if name_l == "theme.conf":
                return (0, rel)
            if name_l == "theme.conf.user":
                return (1, rel)
            if name_l == "metadata.desktop":
                return (2, rel)
            if name_l == "metadata.json":
                return (3, rel)
            if name_l in ("main.qml", "login.qml"):
                return (4, rel)
            if p.suffix.lower() == ".qml":
                return (5, rel)
            return (6, rel)

        discovered_files.sort(key=file_sort_key)

        # Ensure theme.conf is always present in list even if not yet created on disk
        has_theme_conf = any(p.name == "theme.conf" for p in discovered_files)
        if not has_theme_conf:
            discovered_files.insert(0, self.conf_path)

        selected_idx = 0
        for idx, p in enumerate(discovered_files):
            try:
                rel = p.relative_to(self.theme_path).as_posix()
            except ValueError:
                rel = p.name

            # Assign informative icons & label descriptions
            label = rel
            if p.name == "theme.conf":
                label = f"📄 {rel} (Main SDDM Configuration)"
            elif p.name == "theme.conf.user":
                label = f"⚙️ {rel} (User Overrides)"
            elif p.name == "metadata.desktop":
                label = f"🖥️ {rel} (SDDM Desktop Spec)"
            elif p.name == "metadata.json":
                label = f"📋 {rel} (Package Metadata)"
            elif p.name.lower() in ("main.qml", "login.qml"):
                label = f"🧩 {rel} (Greeter Main Script)"
            elif p.suffix.lower() == ".qml":
                label = f"🧩 {rel}"
            else:
                label = f"📄 {rel}"

            self.combo_files.addItem(label, str(p))

            if self._initial_file_name and p.name == self._initial_file_name:
                selected_idx = idx
            elif p.name == current_active and not self._initial_file_name:
                selected_idx = idx

        self._initial_file_name = None
        self.combo_files.blockSignals(False)

        if self.combo_files.count() > 0:
            self.combo_files.setCurrentIndex(selected_idx)
            self.load_file(Path(self.combo_files.itemData(selected_idx)))

    def _on_combo_file_changed(self, index: int):
        if index < 0:
            return
        target_path = Path(self.combo_files.itemData(index))
        if target_path == self.active_file_path:
            return

        if self.is_dirty:
            reply = QMessageBox.question(
                self,
                "Save Changes?",
                f"You have unsaved changes in '{self.active_file_path.name}'. Save changes before switching?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if reply == QMessageBox.StandardButton.Save:
                if not self.save_current_file():
                    # If save failed, block switch
                    self.blockSignals(True)
                    self._restore_combo_selection()
                    self.blockSignals(False)
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                self.combo_files.blockSignals(True)
                self._restore_combo_selection()
                self.combo_files.blockSignals(False)
                return

        self.load_file(target_path)

    def _restore_combo_selection(self):
        for i in range(self.combo_files.count()):
            if Path(self.combo_files.itemData(i)) == self.active_file_path:
                self.combo_files.setCurrentIndex(i)
                break

    def load_file(self, file_path: Path):
        """Loads target file into CodeEditor and configures appropriate syntax highlighting."""
        self.active_file_path = file_path.resolve()

        if self.active_file_path.exists():
            try:
                content = self.active_file_path.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                content = f"# Error reading {self.active_file_path.name}: {e}\n"
        else:
            if self.active_file_path.name == "theme.conf":
                content = "[General]\nbackground=\ntype=image\nfont=\n"
            else:
                content = ""

        # Update syntax highlighting & comment prefix
        self._apply_highlighter_for_file(self.active_file_path)

        self.editor.blockSignals(True)
        self.editor.setPlainText(content)
        self.editor.blockSignals(False)

        self.set_dirty(False)
        self.update_live_preview()

    def _apply_highlighter_for_file(self, file_path: Path):
        suffix = file_path.suffix.lower()
        name = file_path.name.lower()

        # Detach previous highlighters
        if self.ini_highlighter:
            self.ini_highlighter.setDocument(None)
            self.ini_highlighter = None
        if self.qml_highlighter:
            self.qml_highlighter.setDocument(None)
            self.qml_highlighter = None

        if suffix in (".conf", ".ini", ".desktop", ".user", ".orig") or name.startswith("theme.conf"):
            self.ini_highlighter = INISyntaxHighlighter(self.editor.document())
            self.editor.enable_escape_warning = True
            self.editor.comment_prefix = "# "
        elif suffix in (".qml", ".js", ".json"):
            self.qml_highlighter = QMLSyntaxHighlighter(self.editor.document())
            self.editor.enable_escape_warning = False
            self.editor.comment_prefix = "// "
        else:
            self.editor.enable_escape_warning = False
            self.editor.comment_prefix = "# "

        self.editor.line_number_area.update()

    def _on_text_changed(self):
        self.set_dirty(True)
        if self.active_file_path.name == "theme.conf":
            self.preview_timer.start()

    def set_dirty(self, dirty: bool):
        self.is_dirty = dirty
        title = f"Edit: {self.theme_path.name} — {self.active_file_path.name}"
        if self.is_dirty:
            title += " *"
        self.setWindowTitle(title)

    @staticmethod
    def resolve_escape_sequences(val: str) -> str:
        val = val.replace("\\n", "\n")
        val = val.replace("\\t", "\t")
        val = val.replace("\\s", " ")
        val = val.replace("\\\\", "\\")
        return val

    def update_live_preview(self):
        """Re-parses background settings and updates live preview panel."""
        bg_val = ""
        type_val = "image"
        font_val = "default"

        # If currently editing theme.conf, parse live text
        if self.active_file_path.name == "theme.conf":
            text = self.editor.toPlainText()
            in_general = False
            for line in text.split("\n"):
                line_str = line.strip()
                if line_str.startswith("[") and "]" in line_str:
                    sec = line_str[1 : line_str.index("]")].strip().lower()
                    in_general = (sec == "general")
                    continue

                if in_general and "=" in line_str and not line_str.startswith("#"):
                    k, v = line_str.split("=", 1)
                    k = k.strip().lower()
                    v_clean = v.split("#")[0].strip().strip('"').strip("'")
                    if k == "background":
                        bg_val = v_clean
                    elif k == "type":
                        type_val = v_clean
                    elif k == "font":
                        font_val = v_clean
        else:
            # When editing another file (like Main.qml), read background from theme.conf on disk
            if self.conf_path.exists():
                try:
                    for line in self.conf_path.read_text(encoding="utf-8", errors="replace").split("\n"):
                        ls = line.strip()
                        if ls.startswith("background=") or ls.startswith("background ="):
                            bg_val = ls.split("=", 1)[1].split("#")[0].strip().strip('"').strip("'")
                        elif ls.startswith("type=") or ls.startswith("type ="):
                            type_val = ls.split("=", 1)[1].split("#")[0].strip().strip('"').strip("'")
                except Exception:
                    pass

        resolved_bg = self.resolve_escape_sequences(bg_val)

        # Fallback to preview.png if no background setting
        if not resolved_bg:
            for p_cand in ("preview.png", "preview.jpg", "background.png", "background.jpg"):
                if (self.theme_path / p_cand).exists():
                    resolved_bg = p_cand
                    break

        if type_val == "color" or (resolved_bg and resolved_bg.startswith("#")):
            color = QColor(resolved_bg if resolved_bg.startswith("#") else "#1a1b26")
            if color.isValid():
                pix = QPixmap(self.lbl_preview_image.size())
                pix.fill(color)
                self.lbl_preview_image.setPixmap(pix)
                self.lbl_meta_strip.setText(f"type: color | {resolved_bg} | File: {self.active_file_path.name}")
                return

        if not resolved_bg:
            self.lbl_preview_image.setPixmap(QPixmap())
            self.lbl_preview_image.setText("No background set")
            self.lbl_preview_image.setStyleSheet("QLabel { color: #6c7086; font-size: 14px; font-style: italic; }")
            self.lbl_meta_strip.setText(f"Editing: {self.active_file_path.name} | Theme: {self.theme_path.name}")
            return

        bg_path = Path(resolved_bg)
        if not bg_path.is_absolute():
            bg_path = self.theme_path / bg_path

        if not bg_path.exists():
            self.lbl_preview_image.setPixmap(QPixmap())
            self.lbl_preview_image.setText(f"File not found:\n{bg_path.name}")
            self.lbl_preview_image.setStyleSheet("QLabel { color: #f38ba8; font-size: 13px; }")
            self.lbl_meta_strip.setText(f"Editing: {self.active_file_path.name} | Missing: {bg_path.name}")
            return

        if type_val == "video" or bg_path.suffix.lower() in (".mp4", ".webm", ".mkv", ".mov"):
            self.lbl_preview_image.setPixmap(QPixmap())
            self.lbl_preview_image.setText("🎬 Video Background\n" + bg_path.name)
            self.lbl_preview_image.setStyleSheet("QLabel { color: #7aa2f7; font-size: 14px; }")
            file_mb = bg_path.stat().st_size / (1024 * 1024)
            self.lbl_meta_strip.setText(f"type: video | {bg_path.name} | {file_mb:.1f} MB | {self.active_file_path.name}")
            return

        pixmap = QPixmap(str(bg_path))
        if pixmap.isNull():
            self.lbl_preview_image.setPixmap(QPixmap())
            self.lbl_preview_image.setText(f"Could not load image:\n{bg_path.name}")
            self.lbl_preview_image.setStyleSheet("QLabel { color: #f38ba8; font-size: 13px; }")
            self.lbl_meta_strip.setText(f"Editing: {self.active_file_path.name}")
            return

        scaled = pixmap.scaled(
            self.lbl_preview_image.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.lbl_preview_image.setStyleSheet("QLabel { background-color: transparent; }")
        self.lbl_preview_image.setPixmap(scaled)

        file_size_mb = bg_path.stat().st_size / (1024 * 1024)
        size_str = f"{file_size_mb:.1f} MB" if file_size_mb >= 0.1 else f"{bg_path.stat().st_size / 1024:.0f} KB"
        self.lbl_meta_strip.setText(
            f"{pixmap.width()}×{pixmap.height()} | {size_str} | Editing: {self.active_file_path.name}"
        )

    def choose_background(self):
        """Opens file dialog and updates background= in theme.conf."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Background Image",
            str(self.theme_path),
            "Images (*.png *.jpg *.jpeg *.svg *.webp);;Videos (*.mp4 *.webm *.mkv);;All Files (*)",
        )
        if not file_path:
            return

        bg_file = Path(file_path)
        try:
            rel_path = bg_file.relative_to(self.theme_path)
            val_to_insert = str(rel_path)
        except ValueError:
            val_to_insert = str(bg_file)

        # If currently in theme.conf, update editor text directly
        if self.active_file_path.name == "theme.conf":
            text = self.editor.toPlainText()
            lines = text.split("\n")
            replaced = False
            in_general = False
            general_idx = -1

            for i, line in enumerate(lines):
                line_s = line.strip()
                if line_s.startswith("[") and "]" in line_s:
                    sec = line_s[1 : line_s.index("]")].strip().lower()
                    in_general = (sec == "general")
                    if in_general:
                        general_idx = i
                    continue

                if in_general and line_s.startswith("background=") or (in_general and line_s.startswith("background =")):
                    lines[i] = f"background={val_to_insert}"
                    replaced = True
                    break

            if not replaced:
                if general_idx != -1:
                    lines.insert(general_idx + 1, f"background={val_to_insert}")
                else:
                    lines.append("[General]")
                    lines.append(f"background={val_to_insert}")

            self.editor.setPlainText("\n".join(lines))
            self.update_live_preview()
        else:
            # If in another file, switch to theme.conf or write to theme.conf on disk
            reply = QMessageBox.question(
                self,
                "Update theme.conf Background",
                f"Set background={val_to_insert} in theme.conf?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                conf_text = (
                    self.conf_path.read_text(encoding="utf-8", errors="replace")
                    if self.conf_path.exists()
                    else "[General]\nbackground=\n"
                )
                if "background=" in conf_text:
                    conf_text = re.sub(r"background=.*", f"background={val_to_insert}", conf_text)
                else:
                    conf_text += f"\nbackground={val_to_insert}\n"
                ThemeWriter.write_file(self.conf_path, conf_text)
                self.update_live_preview()

    def _on_new_file_clicked(self):
        """Prompts user to create a new file in the theme folder."""
        file_name, ok = QInputDialog.getText(
            self,
            "Create New Theme File",
            "Enter relative file name (e.g., theme.conf.user, CustomButton.qml, README.txt):",
        )
        if not ok or not file_name.strip():
            return

        file_name = file_name.strip()
        if ".." in file_name or file_name.startswith("/"):
            QMessageBox.critical(self, "Invalid Name", "Path traversal components are not allowed.")
            return

        target_file = self.theme_path / file_name
        if target_file.exists():
            QMessageBox.information(self, "File Exists", f"File '{file_name}' already exists.")
            self._initial_file_name = file_name
            self.populate_files()
            return

        # Starter templates based on extension
        starter = ""
        ext = target_file.suffix.lower()
        if ext == ".qml":
            starter = "import QtQuick\nimport QtQuick.Controls\n\nItem {\n    id: root\n}\n"
        elif ext in (".conf", ".ini"):
            starter = "[General]\n"
        elif ext == ".json":
            starter = "{\n}\n"

        write_ok, write_msg = ThemeWriter.write_file(target_file, starter)
        if not write_ok:
            QMessageBox.critical(self, "Create Failed", f"Could not create '{file_name}':\n\n{write_msg}")
            return

        self._initial_file_name = file_name
        self.populate_files()

    def save_current_file(self) -> bool:
        """Writes current editor content to active file."""
        content = self.editor.toPlainText()
        ok, msg = ThemeWriter.write_file(self.active_file_path, content)
        if not ok:
            QMessageBox.critical(self, "Save Failed", f"Could not save {self.active_file_path.name}:\n\n{msg}")
            return False

        self.set_dirty(False)
        self.theme_saved.emit(self.theme_path)

        # Brief notification in title
        self.setWindowTitle(f"Edit: {self.theme_path.name} — {self.active_file_path.name} (Saved)")
        QTimer.singleShot(1500, lambda: self.setWindowTitle(f"Edit: {self.theme_path.name} — {self.active_file_path.name}"))
        return True

    def save_and_apply(self):
        """Saves current file, applies theme to SDDM configuration, restarts SDDM with overlay, and closes."""
        if not self.save_current_file():
            return

        apply_ok, apply_msg = ThemeApplier.apply_theme(self.theme_path.name)
        if not apply_ok:
            QMessageBox.critical(self, "Apply Failed", f"Failed to apply theme config:\n\n{apply_msg}")
            return

        self.show_restarting_overlay()

    def show_restarting_overlay(self):
        """Displays 2-second restarting overlay, triggers polkit restart, then closes."""
        overlay = QFrame(self)
        overlay.setStyleSheet(
            "QFrame {"
            "  background-color: rgba(26, 27, 38, 0.95);"
            "  border-radius: 8px;"
            "}"
        )
        overlay.setGeometry(self.rect())

        vlayout = QVBoxLayout(overlay)
        vlayout.setAlignment(Qt.AlignCenter)

        spinner_lbl = QLabel("⚡ Restarting SDDM Display Manager…", overlay)
        spinner_lbl.setStyleSheet("QLabel { font-size: 18px; font-weight: bold; color: #7aa2f7; }")
        vlayout.addWidget(spinner_lbl)

        sub_lbl = QLabel(f"Applying '{self.theme_path.name}' changes to login screen", overlay)
        sub_lbl.setStyleSheet("QLabel { font-size: 13px; color: #9aa5ce; }")
        vlayout.addWidget(sub_lbl)

        overlay.show()
        QApplication.processEvents()

        ThemeWriter.restart_sddm()
        QTimer.singleShot(2000, self.accept)

    def close_with_check(self):
        if self.is_dirty:
            reply = QMessageBox.question(
                self,
                "Discard Changes?",
                f"You have unsaved changes in '{self.active_file_path.name}'. Discard them?",
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if reply != QMessageBox.StandardButton.Discard:
                return
        self.reject()

    def closeEvent(self, event):
        if self.is_dirty:
            reply = QMessageBox.question(
                self,
                "Discard Changes?",
                f"You have unsaved changes in '{self.active_file_path.name}'. Discard them?",
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if reply != QMessageBox.StandardButton.Discard:
                event.ignore()
                return
        event.accept()
