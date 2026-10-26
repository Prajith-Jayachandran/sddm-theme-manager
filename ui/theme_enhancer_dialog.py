"""
SDDM Theme Manager - Next-Gen Theme Enhancer Dialog
Interactive modal allowing users to equip existing installed themes with modern features:
Startup Boot Chime, GLSL Shaders, Real-Time Weather, MPRIS Media Capsule,
System HUD Telemetry, Sticky Notes, Passkey QR, FIDO2, and Mini-Games.
"""

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.audio_chime import AudioChimeManager
from core.shader_engine import ShaderEngine
from core.theme_enhancer import ThemeEnhancer
from core.theme_scanner import Theme


class ThemeEnhancerDialog(QDialog):
    """Dialog for inspecting, equipping, and reverting Next-Gen features on any existing theme."""

    features_updated = Signal(Path)

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setWindowTitle(f"⚡ Equip Next-Gen Features — {theme.name}")
        self.resize(540, 580)
        self.setMinimumWidth(480)
        self._setup_ui()
        self.refresh_inspection()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        # Header Card
        header = QFrame()
        header.setStyleSheet("background-color: #1a1b26; border-radius: 8px; padding: 12px;")
        h_layout = QVBoxLayout(header)

        title = QLabel(f"⚡ Equip Next-Gen Features: {self.theme.name}")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #7aa2f7;")
        h_layout.addWidget(title)

        desc = QLabel(
            "Upgrade this theme with SDDM Theme Manager's modern sensory and telemetry suite. "
            "A safe backup is created automatically before any files are modified."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #9aa5ce; font-size: 12px;")
        h_layout.addWidget(desc)
        layout.addWidget(header)

        # Feature Selection Group
        grp_features = QGroupBox("Available Next-Gen Features")
        grp_layout = QVBoxLayout(grp_features)
        grp_layout.setSpacing(10)

        # 1. Startup Boot Chime
        chime_row = QHBoxLayout()
        self.chk_boot_chime = QCheckBox("🔊 Startup Boot Chime Audio")
        self.chk_boot_chime.setChecked(True)
        chime_row.addWidget(self.chk_boot_chime)

        self.combo_chime = QComboBox()
        for pid, pinfo in AudioChimeManager.PRESETS.items():
            self.combo_chime.addItem(pinfo["name"], pid)
        chime_row.addWidget(self.combo_chime)

        self.btn_test_sound = QPushButton("▶ Test")
        self.btn_test_sound.setToolTip("Listen to sound preview")
        self.btn_test_sound.clicked.connect(self._play_test_sound)
        chime_row.addWidget(self.btn_test_sound)
        grp_layout.addLayout(chime_row)

        # 2. GLSL Fragment Shader Background
        shader_row = QHBoxLayout()
        self.chk_shader = QCheckBox("🌌 Procedural GLSL Shader Background")
        self.chk_shader.setChecked(True)
        shader_row.addWidget(self.chk_shader)

        self.combo_shader = QComboBox()
        for p in ShaderEngine.get_presets():
            self.combo_shader.addItem(p.name, p.id)
        shader_row.addWidget(self.combo_shader)
        grp_layout.addLayout(shader_row)

        # 3. Weather & Astronomical Cosmos Canvas
        self.chk_weather = QCheckBox("🌧️ Real-Time Weather & Lunar Phase Particle Canvas")
        self.chk_weather.setChecked(True)
        grp_layout.addWidget(self.chk_weather)

        # 4. Pre-Login MPRIS Media Capsule (Dynamic Island)
        self.chk_mpris = QCheckBox("🎵 Pre-Login MPRIS Media Capsule (Dynamic Island)")
        self.chk_mpris.setChecked(True)
        grp_layout.addWidget(self.chk_mpris)

        # 5. Cold Boot System HUD Hardware Telemetry
        self.chk_hud = QCheckBox("📊 Cold Boot System HUD (CPU Temp, RAM, Battery, Updates)")
        self.chk_hud.setChecked(True)
        grp_layout.addWidget(self.chk_hud)

        # 6. Pre-Login Sticky Notes Bulletin
        self.chk_notes = QCheckBox("📝 Household Pre-Login Sticky Notes Bulletin")
        self.chk_notes.setChecked(True)
        grp_layout.addWidget(self.chk_notes)

        # 7. Security: Mobile Passkey QR & FIDO2 Visualizer
        self.chk_security = QCheckBox("📱 Mobile Biometric Passkey QR & 🔑 FIDO2 Visualizer")
        self.chk_security.setChecked(True)
        grp_layout.addWidget(self.chk_security)

        # 8. Pre-Login Retro Mini-Games
        self.chk_games = QCheckBox("🎮 Pre-Login Retro Mini-Games Easter Egg (Ctrl+Alt+G)")
        self.chk_games.setChecked(True)
        grp_layout.addWidget(self.chk_games)

        layout.addWidget(grp_features)

        # Action Buttons
        btn_box = QVBoxLayout()
        btn_box.setSpacing(8)

        # 1-Click Upgrade Button
        self.btn_equip_all = QPushButton("⚡ Equip All Next-Gen Features (1-Click Upgrade)")
        self.btn_equip_all.setStyleSheet(
            "QPushButton { background-color: #7aa2f7; color: #1a1b26; font-weight: bold; padding: 10px; border-radius: 6px; font-size: 13px; }"
            "QPushButton:hover { background-color: #89b4fa; }"
        )
        self.btn_equip_all.clicked.connect(self._on_equip_all_clicked)
        btn_box.addWidget(self.btn_equip_all)

        # Revert Button & Close
        sub_btns = QHBoxLayout()
        self.btn_revert = QPushButton("↺ Revert to Original Theme")
        self.btn_revert.setStyleSheet("color: #f7768e;")
        self.btn_revert.setToolTip("Restore Main.qml from backup and remove injected components")
        self.btn_revert.clicked.connect(self._on_revert_clicked)
        sub_btns.addWidget(self.btn_revert)

        sub_btns.addStretch()

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        sub_btns.addWidget(btn_close)

        btn_box.addLayout(sub_btns)
        layout.addLayout(btn_box)

    def refresh_inspection(self):
        status = ThemeEnhancer.inspect_theme_features(self.theme.path)
        main_qml = ThemeEnhancer.get_main_qml_path(self.theme.path)
        backup_exists = False
        if main_qml:
            backup_file = self.theme.path / (main_qml.name + ThemeEnhancer.BACKUP_SUFFIX)
            backup_exists = backup_file.exists()

        self.btn_revert.setEnabled(backup_exists)

    def _play_test_sound(self):
        preset_id = self.combo_chime.currentData() or "mac_retro"
        ok, msg = AudioChimeManager.play_chime(preset_id)
        if not ok:
            QMessageBox.warning(self, "Audio Preview", msg)

    def _on_equip_all_clicked(self):
        chime_preset = self.combo_chime.currentData() or "mac_retro"
        shader_preset = self.combo_shader.currentData() or "matrix_rain"

        ok, msg = ThemeEnhancer.equip_all_nextgen_features(
            self.theme.path,
            chime_preset=chime_preset,
            shader_preset=shader_preset,
        )
        if ok:
            QMessageBox.information(
                self,
                "Theme Upgraded",
                f"🎉 {msg}\n\n"
                "• Boot Chime: Active on SDDM startup\n"
                "• Shaders, Weather, HUD, and MPRIS: Injected into Main.qml\n"
                "• Safe Backup: Main.qml.pre_enhance_bak created.",
            )
            self.refresh_inspection()
            self.features_updated.emit(self.theme.path)
        else:
            QMessageBox.critical(self, "Upgrade Error", f"Failed to equip features:\n\n{msg}")

    def _on_revert_clicked(self):
        reply = QMessageBox.question(
            self,
            "Confirm Revert",
            f"Are you sure you want to restore '{self.theme.name}' to its original pre-enhanced state?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            ok, msg = ThemeEnhancer.revert_theme_features(self.theme.path)
            if ok:
                QMessageBox.information(self, "Reverted", f"✅ {msg}")
                self.refresh_inspection()
                self.features_updated.emit(self.theme.path)
            else:
                QMessageBox.critical(self, "Revert Error", f"Failed to revert theme:\n\n{msg}")
