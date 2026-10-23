"""
SDDM Theme Manager - SDDM Daemon Settings & Autologin Dialog
GUI for configuring core SDDM daemon options: Autologin, session selection, and NumLock.
"""

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
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.avatar_manager import AvatarManager
from core.daemon_config import DaemonConfigManager


class DaemonConfigDialog(QDialog):
    """Dialog for managing SDDM daemon parameters (autologin, sessions, numlock)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SDDM Daemon Settings — Autologin & Sessions")
        self.setMinimumWidth(440)
        self.config = DaemonConfigManager.read_daemon_config()
        self.sessions = DaemonConfigManager.get_available_sessions()
        self.users = AvatarManager.get_system_users()
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(18, 18, 18, 18)

        # Header
        header = QLabel("SDDM Daemon Control Panel")
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #7aa2f7;")
        main_layout.addWidget(header)

        tabs = QTabWidget()

        # Tab 1: Autologin
        tab_auto = QWidget()
        auto_layout = QVBoxLayout(tab_auto)

        self.chk_autologin = QCheckBox("Enable Automatic Login")
        self.chk_autologin.setChecked(self.config.get("autologin_enabled", False))
        self.chk_autologin.setStyleSheet("font-weight: bold; font-size: 13px;")
        auto_layout.addWidget(self.chk_autologin)

        grp_auto = QGroupBox("Autologin Credentials")
        form_auto = QFormLayout(grp_auto)

        self.combo_user = QComboBox()
        self.combo_user.addItems(self.users)
        cur_user = self.config.get("autologin_user", "")
        idx = self.combo_user.findText(cur_user)
        if idx >= 0:
            self.combo_user.setCurrentIndex(idx)
        form_auto.addRow("User Account:", self.combo_user)

        self.combo_session = QComboBox()
        cur_session = self.config.get("autologin_session", "")
        selected_session_idx = 0
        for i, (disp, filename) in enumerate(self.sessions):
            self.combo_session.addItem(disp, filename)
            if filename == cur_session:
                selected_session_idx = i
        if self.sessions:
            self.combo_session.setCurrentIndex(selected_session_idx)
        form_auto.addRow("Default Session:", self.combo_session)

        self.chk_relogin = QCheckBox("Automatically relogin after session exit")
        self.chk_relogin.setChecked(self.config.get("autologin_relogin", False))
        form_auto.addRow(self.chk_relogin)

        auto_layout.addWidget(grp_auto)
        self.chk_autologin.toggled.connect(grp_auto.setEnabled)
        grp_auto.setEnabled(self.chk_autologin.isChecked())
        auto_layout.addStretch()

        tabs.addTab(tab_auto, "Autologin")

        # Tab 2: General & Sessions
        tab_gen = QWidget()
        gen_layout = QVBoxLayout(tab_gen)

        grp_gen = QGroupBox("Startup & Behavior")
        form_gen = QFormLayout(grp_gen)

        self.combo_numlock = QComboBox()
        self.combo_numlock.addItems(["none", "on", "off"])
        cur_nl = self.config.get("numlock", "none")
        nl_idx = self.combo_numlock.findText(cur_nl)
        if nl_idx >= 0:
            self.combo_numlock.setCurrentIndex(nl_idx)
        form_gen.addRow("NumLock on Boot:", self.combo_numlock)

        self.chk_last_user = QCheckBox("Remember last logged-in user")
        self.chk_last_user.setChecked(self.config.get("remember_last_user", True))
        form_gen.addRow(self.chk_last_user)

        self.chk_last_session = QCheckBox("Remember last selected desktop session")
        self.chk_last_session.setChecked(self.config.get("remember_last_session", True))
        form_gen.addRow(self.chk_last_session)

        gen_layout.addWidget(grp_gen)
        gen_layout.addStretch()

        tabs.addTab(tab_gen, "General")

        main_layout.addWidget(tabs)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_save = QPushButton("Save Settings")
        btn_save.setDefault(True)
        btn_save.setStyleSheet("background-color: #7aa2f7; color: #1a1b26; font-weight: bold; padding: 6px 14px;")
        btn_save.clicked.connect(self._save_settings)
        btn_layout.addWidget(btn_save)

        main_layout.addLayout(btn_layout)

    def _save_settings(self):
        chosen_session_file = self.combo_session.currentData() or ""
        new_cfg = {
            "autologin_enabled": self.chk_autologin.isChecked(),
            "autologin_user": self.combo_user.currentText() if self.chk_autologin.isChecked() else "",
            "autologin_session": chosen_session_file if self.chk_autologin.isChecked() else "",
            "autologin_relogin": self.chk_relogin.isChecked(),
            "numlock": self.combo_numlock.currentText(),
            "remember_last_user": self.chk_last_user.isChecked(),
            "remember_last_session": self.chk_last_session.isChecked(),
        }

        ok, msg = DaemonConfigManager.save_daemon_config(new_cfg)
        if ok:
            QMessageBox.information(self, "Settings Saved", msg)
            self.accept()
        else:
            QMessageBox.critical(self, "Save Error", msg)
