"""
SDDM Theme Manager - OS Chameleon Presets Dialog (Feature 18)
1-Click transformation to macOS Sequoia, Windows 11 Fluent, Steam Deck OLED, or Cyberpunk 2077 HUD.
"""

from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core.chameleon_presets import ChameleonPresetsManager


class ChameleonDialog(QDialog):
    """OS Chameleon 1-Click Distro Hopper Presets Modal."""

    theme_created = Signal(Path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🦎 OS Chameleon Theme Presets")
        self.resize(500, 380)
        self.setMinimumWidth(440)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(18, 18, 18, 18)

        # Header Card
        header = QFrame()
        header.setStyleSheet("background-color: #1a1b26; border-radius: 8px; padding: 12px;")
        h_layout = QVBoxLayout(header)
        title = QLabel("🦎 OS Chameleon Distro-Hopper Presets")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #7aa2f7;")
        h_layout.addWidget(title)

        desc = QLabel(
            "Instantly scaffold pixel-perfect replica themes inspired by other popular operating systems. "
            "Each preset includes dedicated QML layouts, assets, and styling."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #9aa5ce; font-size: 12px;")
        h_layout.addWidget(desc)
        layout.addWidget(header)

        # Preset Selector Box
        box = QFrame()
        box.setStyleSheet("background-color: #16161e; border: 1px solid #292e42; border-radius: 8px; padding: 14px;")
        b_layout = QVBoxLayout(box)
        b_layout.setSpacing(10)

        lbl_select = QLabel("Choose OS Preset:")
        lbl_select.setStyleSheet("font-weight: bold; color: #c0caf5;")
        b_layout.addWidget(lbl_select)

        self.combo_presets = QComboBox()
        self.combo_presets.setStyleSheet("padding: 8px; font-size: 13px;")
        for p in ChameleonPresetsManager.PRESETS:
            self.combo_presets.addItem(f"{p.name} ({p.os_family})", p.id)
        self.combo_presets.currentIndexChanged.connect(self._update_desc)
        b_layout.addWidget(self.combo_presets)

        self.lbl_preset_desc = QLabel("")
        self.lbl_preset_desc.setWordWrap(True)
        self.lbl_preset_desc.setStyleSheet("color: #7aa2f7; font-size: 12px; font-style: italic; min-height: 40px;")
        b_layout.addWidget(self.lbl_preset_desc)

        layout.addWidget(box)
        self._update_desc()

        # Action Buttons
        btn_row = QHBoxLayout()
        self.btn_apply = QPushButton("✨ Create Chameleon Theme")
        self.btn_apply.setStyleSheet(
            "QPushButton { background-color: #7aa2f7; color: #1a1b26; font-weight: bold; padding: 9px 18px; border-radius: 6px; font-size: 13px; }"
            "QPushButton:hover { background-color: #89b4fa; }"
        )
        self.btn_apply.clicked.connect(self._on_create_clicked)
        btn_row.addWidget(self.btn_apply)

        btn_row.addStretch()

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _update_desc(self):
        pid = self.combo_presets.currentData()
        preset = ChameleonPresetsManager.get_preset_by_id(pid)
        if preset:
            self.lbl_preset_desc.setText(f"💡 {preset.description}")

    def _on_create_clicked(self):
        pid = self.combo_presets.currentData()
        preset = ChameleonPresetsManager.get_preset_by_id(pid)
        if not preset:
            return

        dest_dir = Path.home() / f".local/share/sddm/themes/{preset.id}"
        ok, msg = ChameleonPresetsManager.export_preset_to_theme(preset.id, dest_dir)
        if ok:
            QMessageBox.information(
                self,
                "Chameleon Theme Created",
                f"🎉 {preset.name} has been created at:\n{dest_dir}\n\n"
                "You can now select and apply it directly in SDDM Theme Manager!",
            )
            self.theme_created.emit(dest_dir)
            self.accept()
        else:
            QMessageBox.warning(self, "Creation Failed", f"Could not create preset: {msg}")
