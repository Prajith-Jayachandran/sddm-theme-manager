"""
SDDM Theme Manager - Boot Shield Safety & Rollback Dialog
Displays fail-safe verification status, crash diagnostic logs, and manual rollback trigger.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from core.boot_shield import BootShield


class BootShieldDialog(QDialog):
    """Dialog displaying Boot Shield health telemetry and rollback controls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🛡️ SDDM Boot Shield — System Safety Center")
        self.resize(640, 480)
        self._setup_ui()
        self.refresh_telemetry()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Header Banner
        header = QFrame()
        header.setStyleSheet("background-color: #1a1b26; border-radius: 8px; padding: 12px;")
        h_layout = QVBoxLayout(header)

        title = QLabel("🛡️ Boot Shield Watchdog System")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #73daca;")
        h_layout.addWidget(title)

        desc = QLabel(
            "Boot Shield prevents lockouts by monitoring SDDM startup. If a custom theme, shader, "
            "or audio stream crashes SDDM, the system automatically restores a safe fallback theme."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #9aa5ce; font-size: 12px;")
        h_layout.addWidget(desc)
        layout.addWidget(header)

        # Status Summary Label
        self.lbl_status = QLabel("Checking system health…")
        self.lbl_status.setStyleSheet("font-size: 13px; font-weight: bold; padding: 6px 0;")
        layout.addWidget(self.lbl_status)

        # Telemetry / Logs Text Area
        lbl_log = QLabel("Diagnostic & Event Logs:")
        lbl_log.setStyleSheet("font-weight: 600; color: #7aa2f7;")
        layout.addWidget(lbl_log)

        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setStyleSheet("background-color: #16161e; color: #c0caf5; font-family: monospace; font-size: 11px;")
        layout.addWidget(self.txt_logs, 1)

        # Control Buttons
        btn_layout = QHBoxLayout()

        self.btn_verify = QPushButton("🔍 Re-verify Safety")
        self.btn_verify.clicked.connect(self.refresh_telemetry)
        btn_layout.addWidget(self.btn_verify)

        self.btn_rollback = QPushButton("🚨 Trigger Safe Rollback Now")
        self.btn_rollback.setStyleSheet("background-color: #f7768e; color: #1a1b26; font-weight: bold;")
        self.btn_rollback.setToolTip("Immediately restore the verified fallback theme in /etc/sddm.conf.d/10-theme.conf")
        self.btn_rollback.clicked.connect(self._on_emergency_rollback)
        btn_layout.addWidget(self.btn_rollback)

        btn_layout.addStretch()

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

    def refresh_telemetry(self):
        report = BootShield.verify_shield_configuration()
        status_text = f"Status: {report['overall_health']}\n"
        status_text += f"Safe Fallback: {report['fallback_theme']} | Active: {report['active_theme']}"
        self.lbl_status.setText(status_text)

        log_lines = []
        for c in report["checks"]:
            mark = "✅" if c["passed"] else "⚠️"
            log_lines.append(f"{mark} {c['name']}: {c['detail']}")

        log_lines.append("\n--- Recent Shield Events ---")
        recent = BootShield.read_recent_logs(20)
        if recent:
            log_lines.extend(recent)
        else:
            log_lines.append("No crash events recorded. System is healthy.")

        self.txt_logs.setPlainText("\n".join(log_lines))

    def _on_emergency_rollback(self):
        reply = QMessageBox.question(
            self,
            "Confirm Emergency Rollback",
            "Are you sure you want to revert SDDM to the safe default theme immediately?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            ok, msg = BootShield.trigger_emergency_rollback(reason="User initiated from Boot Shield Dialog")
            if ok:
                QMessageBox.information(self, "Rollback Complete", f"✅ {msg}")
                self.refresh_telemetry()
            else:
                QMessageBox.critical(self, "Rollback Failed", f"❌ {msg}")
