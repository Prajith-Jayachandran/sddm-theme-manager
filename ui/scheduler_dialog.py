"""
SDDM Theme Manager - Day / Night Theme Scheduler Dialog
GUI for configuring automated day/night theme transitions.
"""

from PySide6.QtCore import QTime, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTimeEdit,
    QVBoxLayout,
)

from core.scheduler import DayNightScheduler
from core.theme_scanner import ThemeScanner


class SchedulerDialog(QDialog):
    """Dialog for configuring Day / Night automated theme transitions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Day / Night Theme Scheduler — SDDM")
        self.setMinimumWidth(380)
        self.config = DayNightScheduler.read_config()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(18, 18, 18, 18)

        # Header
        header = QLabel("Automatic Day / Night Theme Switching")
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #7aa2f7;")
        layout.addWidget(header)

        desc = QLabel(
            "Automatically switches your SDDM login screen between a light theme during daytime "
            "and a dark theme in the evening using a background systemd user timer."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #a9b1d6; font-size: 12px;")
        layout.addWidget(desc)

        # Enable Switch
        self.chk_enable = QCheckBox("Enable Day / Night Scheduler")
        self.chk_enable.setChecked(self.config.get("enabled", False))
        self.chk_enable.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(self.chk_enable)

        # Settings Group
        grp_settings = QGroupBox("Schedule Settings")
        form = QFormLayout(grp_settings)

        all_themes = ThemeScanner.scan_themes()
        theme_names = [t.name for t in all_themes]

        # Day Theme
        self.combo_day_theme = QComboBox()
        self.combo_day_theme.addItems(theme_names)
        day_val = self.config.get("day_theme", "")
        idx = self.combo_day_theme.findText(day_val)
        if idx >= 0:
            self.combo_day_theme.setCurrentIndex(idx)
        form.addRow("Day Theme (☀️):", self.combo_day_theme)

        # Day Time
        self.time_day = QTimeEdit()
        self.time_day.setDisplayFormat("HH:mm")
        try:
            h, m = map(int, self.config.get("day_time", "07:00").split(":"))
            self.time_day.setTime(QTime(h, m))
        except Exception:
            self.time_day.setTime(QTime(7, 0))
        form.addRow("Day Starts At:", self.time_day)

        # Night Theme
        self.combo_night_theme = QComboBox()
        self.combo_night_theme.addItems(theme_names)
        night_val = self.config.get("night_theme", "")
        idx = self.combo_night_theme.findText(night_val)
        if idx >= 0:
            self.combo_night_theme.setCurrentIndex(idx)
        form.addRow("Night Theme (🌙):", self.combo_night_theme)

        # Night Time
        self.time_night = QTimeEdit()
        self.time_night.setDisplayFormat("HH:mm")
        try:
            h, m = map(int, self.config.get("night_time", "19:00").split(":"))
            self.time_night.setTime(QTime(h, m))
        except Exception:
            self.time_night.setTime(QTime(19, 0))
        form.addRow("Night Starts At:", self.time_night)

        layout.addWidget(grp_settings)

        # Toggle enabled state
        self.chk_enable.toggled.connect(grp_settings.setEnabled)
        grp_settings.setEnabled(self.chk_enable.isChecked())

        # Test Apply Button
        btn_test = QPushButton("⚡ Test Scheduled Theme Now")
        btn_test.clicked.connect(self._test_now)
        layout.addWidget(btn_test)

        layout.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_save = QPushButton("Save Schedule")
        btn_save.setDefault(True)
        btn_save.setStyleSheet("background-color: #7aa2f7; color: #1a1b26; font-weight: bold; padding: 6px 14px;")
        btn_save.clicked.connect(self._save_config)
        btn_layout.addWidget(btn_save)

        layout.addLayout(btn_layout)

    def _test_now(self):
        # Save temporary config and test
        self._save_to_dict()
        ok, msg = DayNightScheduler.apply_scheduled(force=True, custom_cfg=self.config)
        if ok:
            QMessageBox.information(self, "Test Successful", f"Applied scheduled theme:\n{msg}")
        else:
            QMessageBox.warning(self, "Test Notice", f"Scheduled theme check:\n{msg}")

    def _save_to_dict(self):
        self.config["enabled"] = self.chk_enable.isChecked()
        self.config["day_theme"] = self.combo_day_theme.currentText()
        self.config["day_time"] = self.time_day.time().toString("HH:mm")
        self.config["night_theme"] = self.combo_night_theme.currentText()
        self.config["night_time"] = self.time_night.time().toString("HH:mm")

    def _save_config(self):
        self._save_to_dict()
        ok, msg = DayNightScheduler.save_config(self.config)
        if ok:
            QMessageBox.information(self, "Schedule Saved", "Day / Night theme schedule updated successfully!")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", msg)
