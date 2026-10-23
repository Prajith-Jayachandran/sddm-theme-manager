"""
SDDM Theme Manager - Visual Theme Tweaker Dialog
Interactive configuration modal for adjusting theme visual parameters:
Clock formatting, form placement, background blur & dimming, fonts, and accents.
"""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QFontComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
)

from core.color_palette import ColorPaletteManager
from core.theme_configurator import ThemeConfigurator
from core.theme_scanner import Theme


class ThemeTweakerDialog(QDialog):
    """Dialog for fine-tuning theme visual parameters."""

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setWindowTitle(f"Theme Tweaker — {theme.name}")
        self.setMinimumWidth(440)
        self.setObjectName("tweakerDialog")

        self.current_tweaks = ThemeConfigurator.read_tweaks(self.theme.path)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(18, 18, 18, 18)

        # Header
        header = QLabel(f"Customize Visuals for '{self.theme.name}'")
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #7aa2f7;")
        main_layout.addWidget(header)

        # 1. Clock & Time Format
        grp_clock = QGroupBox("Clock & Date")
        clock_layout = QFormLayout(grp_clock)

        self.chk_show_clock = QCheckBox("Show Clock")
        self.chk_show_clock.setChecked(self.current_tweaks.get("show_clock", True))
        clock_layout.addRow(self.chk_show_clock)

        self.chk_show_seconds = QCheckBox("Show Seconds")
        self.chk_show_seconds.setChecked(self.current_tweaks.get("show_seconds", False))
        clock_layout.addRow(self.chk_show_seconds)

        self.combo_clock_format = QComboBox()
        self.combo_clock_format.addItems(["24-Hour (HH:mm)", "12-Hour (hh:mm AP)", "Custom"])
        cur_fmt = self.current_tweaks.get("clock_format", "24h")
        if "12" in cur_fmt.lower() or "ap" in cur_fmt.lower():
            self.combo_clock_format.setCurrentIndex(1)
        else:
            self.combo_clock_format.setCurrentIndex(0)
        clock_layout.addRow("Format:", self.combo_clock_format)

        main_layout.addWidget(grp_clock)

        # 2. Layout & Positioning
        grp_layout = QGroupBox("Layout & Positioning")
        pos_layout = QFormLayout(grp_layout)

        self.combo_position = QComboBox()
        self.combo_position.addItems(["Center", "Left", "Right"])
        cur_pos = self.current_tweaks.get("form_position", "center").capitalize()
        idx = self.combo_position.findText(cur_pos)
        if idx >= 0:
            self.combo_position.setCurrentIndex(idx)
        pos_layout.addRow("Login Box Alignment:", self.combo_position)

        self.chk_password_reveal = QCheckBox("Show Password Reveal Button")
        self.chk_password_reveal.setChecked(self.current_tweaks.get("show_password_reveal", True))
        pos_layout.addRow(self.chk_password_reveal)

        main_layout.addWidget(grp_layout)

        # 3. Effects & Visuals
        grp_effects = QGroupBox("Visual Effects & Background")
        eff_layout = QFormLayout(grp_effects)

        # Blur slider
        self.slider_blur = QSlider(Qt.Horizontal)
        self.slider_blur.setRange(0, 50)
        self.slider_blur.setValue(self.current_tweaks.get("blur_radius", 0))
        self.lbl_blur_val = QLabel(f"{self.slider_blur.value()} px")
        self.slider_blur.valueChanged.connect(lambda v: self.lbl_blur_val.setText(f"{v} px"))
        h_blur = QHBoxLayout()
        h_blur.addWidget(self.slider_blur, 1)
        h_blur.addWidget(self.lbl_blur_val)
        eff_layout.addRow("Background Blur:", h_blur)

        # Dim slider
        self.slider_dim = QSlider(Qt.Horizontal)
        self.slider_dim.setRange(0, 80)
        cur_dim = int(self.current_tweaks.get("dim_opacity", 0.0) * 100)
        self.slider_dim.setValue(cur_dim)
        self.lbl_dim_val = QLabel(f"{cur_dim}%")
        self.slider_dim.valueChanged.connect(lambda v: self.lbl_dim_val.setText(f"{v}%"))
        h_dim = QHBoxLayout()
        h_dim.addWidget(self.slider_dim, 1)
        h_dim.addWidget(self.lbl_dim_val)
        eff_layout.addRow("Background Dimming:", h_dim)

        main_layout.addWidget(grp_effects)

        # 4. Typography & Accents
        grp_type = QGroupBox("Typography & Accents")
        type_layout = QFormLayout(grp_type)

        self.combo_font = QFontComboBox()
        cur_font = self.current_tweaks.get("font_family", "")
        if cur_font:
            self.combo_font.setCurrentFont(cur_font)
        type_layout.addRow("Font Family:", self.combo_font)

        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(8, 32)
        self.spin_font_size.setValue(self.current_tweaks.get("font_size", 11))
        type_layout.addRow("Base Font Size:", self.spin_font_size)

        # Accent Color Picker
        self.btn_color = QPushButton("Choose Color…")
        self.selected_color = self.current_tweaks.get("accent_color", "#7aa2f7")
        self._update_color_button()
        self.btn_color.clicked.connect(self._pick_color)

        # Pywal button
        btn_pywal = QPushButton("🪄 Pywal")
        btn_pywal.setToolTip("Import color palette from Pywal cache")
        btn_pywal.clicked.connect(self._import_pywal)

        h_color = QHBoxLayout()
        h_color.addWidget(self.btn_color, 1)
        h_color.addWidget(btn_pywal)
        type_layout.addRow("Accent Color:", h_color)

        main_layout.addWidget(grp_type)

        # Bottom Buttons
        btn_layout = QHBoxLayout()

        btn_reset = QPushButton("Reset Defaults")
        btn_reset.setToolTip("Restore original theme settings and remove visual tweaks")
        btn_reset.clicked.connect(self._on_reset)
        btn_layout.addWidget(btn_reset)

        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_save = QPushButton("Save & Apply")
        btn_save.setDefault(True)
        btn_save.setStyleSheet("background-color: #7aa2f7; color: #1a1b26; font-weight: bold; padding: 6px 14px;")
        btn_save.clicked.connect(self._on_save)
        btn_layout.addWidget(btn_save)

        main_layout.addLayout(btn_layout)

    def _on_reset(self):
        reply = QMessageBox.question(
            self,
            "Reset Tweaks",
            f"Reset all visual tweaks for '{self.theme.name}' to default?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            ok, msg = ThemeConfigurator.reset_tweaks(self.theme.path)
            if ok:
                QMessageBox.information(self, "Tweaks Reset", msg)
                self.accept()
            else:
                QMessageBox.critical(self, "Error", msg)

    def _update_color_button(self):
        col = self.selected_color or "#7aa2f7"
        self.btn_color.setStyleSheet(
            f"background-color: {col}; color: #1a1b26; font-weight: bold; border: 1px solid #414868; border-radius: 4px;"
        )
        self.btn_color.setText(col)

    def _pick_color(self):
        initial = QColor(self.selected_color) if self.selected_color else QColor("#7aa2f7")
        chosen = QColorDialog.getColor(initial, self, "Select Accent Color")
        if chosen.isValid():
            self.selected_color = chosen.name()
            self._update_color_button()

    def _import_pywal(self):
        wal_data = ColorPaletteManager.get_pywal_colors()
        if not wal_data or "colors" not in wal_data:
            QMessageBox.information(
                self,
                "Pywal",
                "No Pywal color cache found at ~/.cache/wal/colors.json.\nRun 'wal -i <image>' first.",
            )
            return

        accent = wal_data["colors"].get("color4") or wal_data["colors"].get("color2")
        if accent:
            self.selected_color = accent
            self._update_color_button()
            QMessageBox.information(self, "Pywal", f"Imported accent color: {accent}")

    def _on_save(self):
        tweaks = {
            "show_clock": self.chk_show_clock.isChecked(),
            "show_seconds": self.chk_show_seconds.isChecked(),
            "clock_format": "12h" if self.combo_clock_format.currentIndex() == 1 else "24h",
            "form_position": self.combo_position.currentText().lower(),
            "show_password_reveal": self.chk_password_reveal.isChecked(),
            "blur_radius": self.slider_blur.value(),
            "dim_opacity": self.slider_dim.value() / 100.0,
            "font_family": self.combo_font.currentFont().family(),
            "font_size": self.spin_font_size.value(),
            "accent_color": self.selected_color,
        }

        ok, msg = ThemeConfigurator.apply_tweaks(self.theme.path, tweaks)
        if ok:
            QMessageBox.information(self, "Tweaks Applied", "Visual theme tweaks saved successfully!")
            self.accept()
        else:
            QMessageBox.critical(self, "Error Saving Tweaks", msg)
