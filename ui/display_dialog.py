"""
SDDM Theme Manager - Multi-Monitor Display Dialog
GUI for selecting and designating the primary display output for SDDM.
"""

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core.display_manager import DisplayManager


class DisplayDialog(QDialog):
    """Dialog for configuring primary screen output for SDDM."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Multi-Monitor Display Setup — SDDM")
        self.setMinimumWidth(400)
        self.monitors = DisplayManager.get_connected_monitors()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(18, 18, 18, 18)

        # Title
        title = QLabel("SDDM Primary Monitor Configuration")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #7aa2f7;")
        layout.addWidget(title)

        desc = QLabel(
            "Select which display should host the primary SDDM login greeter on multi-monitor setups. "
            "This updates /usr/share/sddm/scripts/Xsetup."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #a9b1d6; font-size: 12px;")
        layout.addWidget(desc)

        # Settings
        grp = QGroupBox("Connected Displays")
        form = QFormLayout(grp)

        self.combo_monitors = QComboBox()
        configured_primary = DisplayManager.get_configured_primary()

        selected_idx = 0
        for idx, m in enumerate(self.monitors):
            label = f"{m.name}"
            if m.current_mode:
                label += f" ({m.current_mode})"
            if m.is_primary or m.name == configured_primary:
                label += " [Primary]"
                selected_idx = idx
            self.combo_monitors.addItem(label, m)

        self.combo_monitors.setCurrentIndex(selected_idx)
        self.combo_monitors.currentIndexChanged.connect(self._on_monitor_changed)
        form.addRow("Primary Screen:", self.combo_monitors)

        self.combo_mode = QComboBox()
        self.combo_mode.addItem("Default / Native", None)
        form.addRow("Resolution Mode:", self.combo_mode)

        layout.addWidget(grp)
        self._on_monitor_changed()

        layout.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_save = QPushButton("Apply to SDDM")
        btn_save.setDefault(True)
        btn_save.setStyleSheet("background-color: #7aa2f7; color: #1a1b26; font-weight: bold; padding: 6px 14px;")
        btn_save.clicked.connect(self._apply_display)
        btn_layout.addWidget(btn_save)

        layout.addLayout(btn_layout)

    def _on_monitor_changed(self):
        self.combo_mode.clear()
        self.combo_mode.addItem("Default / Native", None)
        m = self.combo_monitors.currentData()
        if m and m.available_modes:
            for mode in m.available_modes:
                self.combo_mode.addItem(mode, mode)

    def _apply_display(self):
        m = self.combo_monitors.currentData()
        if not m:
            return

        mode = self.combo_mode.currentData()
        ok, msg = DisplayManager.set_primary_monitor(m.name, mode=mode)
        if ok:
            QMessageBox.information(self, "Display Configured", msg)
            self.accept()
        else:
            QMessageBox.critical(self, "Display Error", msg)
