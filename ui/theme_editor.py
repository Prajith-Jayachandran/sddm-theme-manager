"""
SDDM Theme Manager - Theme Editor Dialog
Full-featured INI editor for SDDM theme.conf with syntax highlighting,
line numbers, live background preview, escape sequence resolution, and polkit integration.
"""

import os
import re
from pathlib import Path
from typing import Optional, Set

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
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.polkit import write_file_privileged
from core.theme_applier import ThemeApplier
from ui.theme_writer import ThemeWriter


class INISyntaxHighlighter(QSyntaxHighlighter):
    """
    Syntax highlighter for SDDM theme.conf INI files.
    - [Section] : #89b4fa, bold
    - key       : #a6e3a1, normal
    - =         : #f9e2af, normal
    - value     : #cdd6f4, normal
    - # comment : #6c7086, italic
    - Empty val : #f38ba8, underline
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rules = []

        # Comment format
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#6c7086"))
        self.comment_format.setFontItalic(True)

        # Section format
        self.section_format = QTextCharFormat()
        self.section_format.setForeground(QColor("#89b4fa"))
        self.section_format.setFontWeight(QFont.Bold)

        # Key format
        self.key_format = QTextCharFormat()
        self.key_format.setForeground(QColor("#a6e3a1"))

        # Operator '=' format
        self.operator_format = QTextCharFormat()
        self.operator_format.setForeground(QColor("#f9e2af"))

        # Value format
        self.value_format = QTextCharFormat()
        self.value_format.setForeground(QColor("#cdd6f4"))

        # Empty value missing format
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
                # Any trailing comment on section line
                comment_idx = text.find("#", end_idx)
                if comment_idx != -1:
                    self.setFormat(comment_idx, len(text) - comment_idx, self.comment_format)
                return

        # Key = Value pairs
        eq_idx = text.find("=")
        if eq_idx != -1:
            # Highlight key
            key_text = text[:eq_idx]
            self.setFormat(0, eq_idx, self.key_format)

            # Highlight operator =
            self.setFormat(eq_idx, 1, self.operator_format)

            # Highlight value
            val_text = text[eq_idx + 1 :]
            val_start = eq_idx + 1

            # Check if there is an inline comment
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
                    # Empty value underline
                    self.setFormat(val_start, len(actual_val), self.empty_val_format)
                else:
                    self.setFormat(val_start, len(actual_val), self.value_format)
                self.setFormat(val_start + inline_comment_idx, len(comment_part), self.comment_format)
            else:
                if not val_text.strip():
                    # Empty value underline (signals missing)
                    self.setFormat(val_start, max(1, len(val_text)), self.empty_val_format)
                else:
                    self.setFormat(val_start, len(val_text), self.value_format)


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

        # Font configuration
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        for cand in ["JetBrains Mono", "Fira Code", "DejaVu Sans Mono", "monospace"]:
            if cand in QFontDatabase.families():
                font.setFamily(cand)
                break
        font.setPointSize(11)
        self.setFont(font)

        # Style editor
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
        text = self.toPlainText()
        lines = text.split("\n")
        valid_escapes = {"n", "t", "r", "\\", "s", ";", "#", '"', "'", "x"}

        for idx, line in enumerate(lines):
            # Scan for backslashes in value part
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

                # Check if current line has invalid escape sequence
                if line_num in self.invalid_escape_lines:
                    # Draw warning badge ⚠️
                    painter.drawText(2, top + self.fontMetrics().ascent(), "⚠️")

                # Line number text
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
        # Tab -> 4 spaces
        if event.key() == Qt.Key_Tab:
            self.insertPlainText("    ")
            return
        # Ctrl+/ -> Toggle comment
        if event.key() == Qt.Key_Slash and event.modifiers() == Qt.ControlModifier:
            self.toggle_comment()
            return
        super().keyPressEvent(event)

    def toggle_comment(self):
        """Prepends or removes '# ' on selected lines."""
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

        for b_num in range(start_block, end_block + 1):
            block = doc.findBlockByNumber(b_num)
            text = block.text()
            b_cursor = QTextCursor(block)
            b_cursor.movePosition(QTextCursor.StartOfLine)

            if text.startswith("# "):
                b_cursor.deleteChar()
                b_cursor.deleteChar()
            elif text.startswith("#"):
                b_cursor.deleteChar()
            else:
                b_cursor.insertText("# ")

        cursor.endEditBlock()


class ThemeEditor(QDialog):
    """
    Separate 900x620 dark Theme Editor modal dialog.
    Split: 55% code editor / 45% live preview with debounced updates,
    escape sequence parsing, and bottom toolbar.
    """

    theme_saved = Signal(Path)

    def __init__(self, theme_path: Path | str, parent=None):
        super().__init__(parent)
        self.theme_path = Path(theme_path).resolve()
        self.conf_path = self.theme_path / "theme.conf"
        self.is_dirty = False

        self.setWindowTitle(f"Edit: {self.theme_path.name}")
        self.resize(900, 620)
        self.setMinimumSize(800, 500)

        # Apply dark Tokyo Night theme
        self.setStyleSheet(
            "QDialog {"
            "  background-color: #1a1b26;"
            "  color: #c0caf5;"
            "}"
            "QLabel {"
            "  color: #c0caf5;"
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

        # Setup debounced preview timer (300ms)
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(300)
        self.preview_timer.timeout.connect(self.update_live_preview)

        self._build_ui()
        self._load_conf()
        self._setup_shortcuts()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Splitter (55% left, 45% right)
        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setStyleSheet("QSplitter::handle { background-color: #24283b; width: 4px; }")

        # Left panel: Code Editor
        left_widget = QWidget(self)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        editor_lbl = QLabel(f"<b>Configuration</b> (<code>{self.conf_path.name}</code>)")
        left_layout.addWidget(editor_lbl)

        self.editor = CodeEditor(left_widget)
        self.highlighter = INISyntaxHighlighter(self.editor.document())
        self.editor.textChanged.connect(self._on_text_changed)
        left_layout.addWidget(self.editor, 1)

        splitter.addWidget(left_widget)

        # Right panel: Live Preview
        right_widget = QWidget(self)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        preview_header = QLabel("<b>Live Preview</b>")
        right_layout.addWidget(preview_header)

        # Preview card container
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

        # Set 55% / 45% proportions
        splitter.setSizes([495, 405])
        main_layout.addWidget(splitter, 1)

        # Bottom Toolbar
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(10)

        self.btn_save_apply = QPushButton("⚡ Save & Apply")
        self.btn_save_apply.setObjectName("saveApplyBtn")
        self.btn_save_apply.setToolTip("Save theme.conf and apply to SDDM (Ctrl+S)")
        self.btn_save_apply.clicked.connect(self.save_and_apply)
        bottom_bar.addWidget(self.btn_save_apply)

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
        # Ctrl+S: Save & Apply
        sc_save = QShortcut(QKeySequence("Ctrl+S"), self)
        sc_save.activated.connect(self.save_and_apply)

        # Ctrl+B: Choose Background
        sc_bg = QShortcut(QKeySequence("Ctrl+B"), self)
        sc_bg.activated.connect(self.choose_background)

        # Esc: Close with confirmation
        sc_esc = QShortcut(QKeySequence("Escape"), self)
        sc_esc.activated.connect(self.close_with_check)

    def _load_conf(self):
        """Loads existing theme.conf or creates initial default structure."""
        if self.conf_path.exists():
            try:
                content = self.conf_path.read_text(encoding="utf-8", errors="replace")
                self.editor.setPlainText(content)
            except Exception as e:
                self.editor.setPlainText(f"# Error reading {self.conf_path}: {e}\n[General]\nbackground=\ntype=image\nfont=\n")
        else:
            default_content = (
                "[General]\n"
                "background=\n"
                "type=image\n"
                "font=\n"
            )
            self.editor.setPlainText(default_content)

        self.set_dirty(False)
        self.update_live_preview()

    def _on_text_changed(self):
        self.set_dirty(True)
        self.preview_timer.start()

    def set_dirty(self, dirty: bool):
        self.is_dirty = dirty
        title = f"Edit: {self.theme_path.name}"
        if self.is_dirty:
            title += " *"
        self.setWindowTitle(title)

    @staticmethod
    def resolve_escape_sequences(val: str) -> str:
        """Resolves QSettings INI escape sequences (\\n, \\t, \\s, \\\\)."""
        val = val.replace("\\n", "\n")
        val = val.replace("\\t", "\t")
        val = val.replace("\\s", " ")
        val = val.replace("\\\\", "\\")
        return val

    def update_live_preview(self):
        """Re-parses background=, type=, font= and updates live preview label."""
        text = self.editor.toPlainText()
        bg_val = ""
        type_val = "image"
        font_val = "default"

        in_general = False
        for line in text.split("\n"):
            line_str = line.strip()
            if line_str.startswith("[") and "]" in line_str:
                section_name = line_str[1 : line_str.index("]")].strip().lower()
                in_general = (section_name == "general")
                continue

            if in_general and "=" in line_str and not line_str.startswith("#"):
                k, v = line_str.split("=", 1)
                k = k.strip().lower()
                # Strip inline comment
                v_clean = v.split("#")[0].strip().strip('"').strip("'")
                if k == "background":
                    bg_val = v_clean
                elif k == "type":
                    type_val = v_clean
                elif k == "font":
                    font_val = v_clean

        # Resolve escape sequences
        resolved_bg = self.resolve_escape_sequences(bg_val)

        # Handle type=color
        if type_val == "color" or resolved_bg.startswith("#"):
            color = QColor(resolved_bg if resolved_bg.startswith("#") else "#1a1b26")
            if color.isValid():
                pix = QPixmap(self.lbl_preview_image.size())
                pix.fill(color)
                self.lbl_preview_image.setPixmap(pix)
                self.lbl_meta_strip.setText(f"type: color | {resolved_bg} | font: {font_val}")
                return

        # Handle image / video
        if not resolved_bg:
            self.lbl_preview_image.setPixmap(QPixmap())
            self.lbl_preview_image.setText("No background set")
            self.lbl_preview_image.setStyleSheet("QLabel { color: #6c7086; font-size: 14px; font-style: italic; }")
            self.lbl_meta_strip.setText(f"type: {type_val} | No file selected | font: {font_val}")
            return

        # Resolve path: relative against theme_path or absolute
        bg_path = Path(resolved_bg)
        if not bg_path.is_absolute():
            bg_path = self.theme_path / bg_path

        if not bg_path.exists():
            self.lbl_preview_image.setPixmap(QPixmap())
            self.lbl_preview_image.setText(f"File not found:\n{bg_path.name}")
            self.lbl_preview_image.setStyleSheet("QLabel { color: #f38ba8; font-size: 13px; }")
            self.lbl_meta_strip.setText(f"type: {type_val} | Missing file | font: {font_val}")
            return

        # If video type
        if type_val == "video" or bg_path.suffix.lower() in (".mp4", ".webm", ".mkv", ".mov"):
            self.lbl_preview_image.setPixmap(QPixmap())
            self.lbl_preview_image.setText("🎬 Video Background\n" + bg_path.name)
            self.lbl_preview_image.setStyleSheet("QLabel { color: #7aa2f7; font-size: 14px; }")
            file_mb = bg_path.stat().st_size / (1024 * 1024)
            self.lbl_meta_strip.setText(f"type: video | {bg_path.name} | {file_mb:.1f} MB")
            return

        # Image type
        pixmap = QPixmap(str(bg_path))
        if pixmap.isNull():
            self.lbl_preview_image.setPixmap(QPixmap())
            self.lbl_preview_image.setText(f"Could not load image:\n{bg_path.name}")
            self.lbl_preview_image.setStyleSheet("QLabel { color: #f38ba8; font-size: 13px; }")
            self.lbl_meta_strip.setText(f"type: {type_val} | Corrupt or unsupported")
            return

        scaled = pixmap.scaled(
            self.lbl_preview_image.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.lbl_preview_image.setStyleSheet("QLabel { background-color: transparent; }")
        self.lbl_preview_image.setPixmap(scaled)

        # File metadata
        file_size_mb = bg_path.stat().st_size / (1024 * 1024)
        size_str = f"{file_size_mb:.1f} MB" if file_size_mb >= 0.1 else f"{bg_path.stat().st_size / 1024:.0f} KB"
        self.lbl_meta_strip.setText(
            f"type: {type_val} | {pixmap.width()}×{pixmap.height()} | {size_str} | font: {font_val}"
        )

    def choose_background(self):
        """Opens file dialog and updates or inserts background= line in editor."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Background Image",
            str(self.theme_path),
            "Images (*.png *.jpg *.jpeg *.svg *.webp);;Videos (*.mp4 *.webm *.mkv);;All Files (*)",
        )
        if not file_path:
            return

        bg_file = Path(file_path)
        # If image is inside theme directory, use relative path, else absolute
        try:
            rel_path = bg_file.relative_to(self.theme_path)
            val_to_insert = str(rel_path)
        except ValueError:
            val_to_insert = str(bg_file)

        # Insert or replace background= line in text
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

    def save_and_apply(self):
        """Writes theme.conf to disk, applies to SDDM, restarts SDDM with overlay, and closes."""
        content = self.editor.toPlainText()

        # 1. Write theme.conf
        ok, msg = ThemeWriter.write_file(self.conf_path, content)
        if not ok:
            QMessageBox.critical(self, "Save Failed", f"Could not save {self.conf_path.name}:\n\n{msg}")
            return

        self.set_dirty(False)
        self.theme_saved.emit(self.theme_path)

        # 2. Write drop-in SDDM configuration /etc/sddm.conf.d/10-theme.conf
        apply_ok, apply_msg = ThemeApplier.apply_theme(self.theme_path.name)
        if not apply_ok:
            QMessageBox.critical(self, "Apply Failed", f"Failed to apply theme config:\n\n{apply_msg}")
            return

        # 3. Show 2s "Restarting SDDM…" overlay
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

        sub_lbl = QLabel("Applying new theme.conf changes to login screen", overlay)
        sub_lbl.setStyleSheet("QLabel { font-size: 13px; color: #9aa5ce; }")
        vlayout.addWidget(sub_lbl)

        overlay.show()
        QApplication.processEvents()

        # Trigger restart in polkit / D-Bus
        ThemeWriter.restart_sddm()

        # Close dialog after 2 seconds
        QTimer.singleShot(2000, self.accept)

    def close_with_check(self):
        if self.is_dirty:
            reply = QMessageBox.question(
                self,
                "Discard Changes?",
                f"You have unsaved changes in '{self.theme_path.name}'. Discard them?",
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
                f"You have unsaved changes in '{self.theme_path.name}'. Discard them?",
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if reply != QMessageBox.StandardButton.Discard:
                event.ignore()
                return
        event.accept()
