"""
SDDM Theme Manager - Security & Authentication Suite Dialog (Features 6, 7, 8, 9)
Configures Mobile Passkey QR server, FIDO2 USB hardware tokens, Panic Decoy PIN, and BLE Proximity.
"""

import webbrowser
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.ble_proximity import BLEProximityManager
from core.fido2_detector import FIDO2Detector
from core.panic_mode import PanicModeConfig, PanicModeManager
from core.passkey_server import PasskeyAuthServer


class SecurityDialog(QDialog):
    """Security & Authentication Suite Center."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔐 Security & Authentication Center")
        self.resize(560, 480)
        self.setMinimumWidth(480)
        self._setup_ui()
        self.refresh_all_status()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        # Header Card
        header = QFrame()
        header.setStyleSheet("background-color: #1a1b26; border-radius: 8px; padding: 12px;")
        h_layout = QVBoxLayout(header)
        title = QLabel("🔐 Security & Authentication Suite")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #7aa2f7;")
        h_layout.addWidget(title)

        desc = QLabel(
            "Hardware-backed and cryptographic authentication features for SDDM: "
            "Biometric mobile passkeys, USB hardware keys, BLE proximity, and panic duress sandboxing."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #9aa5ce; font-size: 12px;")
        h_layout.addWidget(desc)
        layout.addWidget(header)

        # Tabs
        self.tabs = QTabWidget()

        # Tab 1: Mobile Passkey QR (Feature 6)
        tab_passkey = QWidget()
        tp_layout = QVBoxLayout(tab_passkey)
        tp_layout.setSpacing(10)

        lbl_pk_desc = QLabel(
            "Enables passwordless biometric mobile authentication at the SDDM greeter screen. "
            "Scan the QR code with your mobile camera and tap your phone's fingerprint sensor to log in."
        )
        lbl_pk_desc.setWordWrap(True)
        lbl_pk_desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        tp_layout.addWidget(lbl_pk_desc)

        pk_box = QGroupBox("Passkey HTTP Authentication Server")
        pk_box_l = QVBoxLayout(pk_box)

        self.lbl_server_status = QLabel("Server: Running on http://localhost:8089")
        self.lbl_server_status.setStyleSheet("font-weight: bold; color: #4ade80;")
        pk_box_l.addWidget(self.lbl_server_status)

        pk_btn_row = QHBoxLayout()
        self.btn_test_passkey = QPushButton("📱 Open Mobile Unlock Preview in Browser")
        self.btn_test_passkey.setStyleSheet("background-color: #2e3c64; color: #7aa2f7; padding: 8px; border-radius: 4px; font-weight: bold;")
        self.btn_test_passkey.clicked.connect(self._on_test_passkey_clicked)
        pk_btn_row.addWidget(self.btn_test_passkey)
        pk_box_l.addLayout(pk_btn_row)

        tp_layout.addWidget(pk_box)
        tp_layout.addStretch()
        self.tabs.addTab(tab_passkey, "📱 Passkey QR")

        # Tab 2: FIDO2 / YubiKey (Feature 9)
        tab_fido = QWidget()
        tf_layout = QVBoxLayout(tab_fido)
        tf_layout.setSpacing(10)

        lbl_fido_desc = QLabel(
            "Detects connected FIDO2 / U2F hardware security keys (YubiKey, SoloKey, Nitrokey, Feitian) "
            "and displays a live holographic presence indicator on the SDDM login screen."
        )
        lbl_fido_desc.setWordWrap(True)
        lbl_fido_desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        tf_layout.addWidget(lbl_fido_desc)

        fido_box = QGroupBox("Hardware Token Status")
        fido_box_l = QVBoxLayout(fido_box)

        self.lbl_fido_status = QLabel("Scanning USB buses…")
        self.lbl_fido_status.setStyleSheet("font-size: 13px; font-weight: bold;")
        fido_box_l.addWidget(self.lbl_fido_status)

        self.btn_rescan_fido = QPushButton("🔄 Rescan USB Hardware Keys")
        self.btn_rescan_fido.clicked.connect(self.refresh_fido_status)
        fido_box_l.addWidget(self.btn_rescan_fido)

        tf_layout.addWidget(fido_box)
        tf_layout.addStretch()
        self.tabs.addTab(tab_fido, "🔑 FIDO2 / YubiKey")

        # Tab 3: Panic Mode / Decoy Duress (Feature 8)
        tab_panic = QWidget()
        tpan_layout = QVBoxLayout(tab_panic)
        tpan_layout.setSpacing(10)

        lbl_pan_desc = QLabel(
            "Protects your privacy under coercion. If your decoy PIN is entered at the SDDM login screen, "
            "the system boots into an ephemeral guest sandbox with zero access to your private files."
        )
        lbl_pan_desc.setWordWrap(True)
        lbl_pan_desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        tpan_layout.addWidget(lbl_pan_desc)

        pan_box = QGroupBox("Decoy PIN Configuration")
        pan_box_l = QVBoxLayout(pan_box)

        row_pin = QHBoxLayout()
        row_pin.addWidget(QLabel("Set Decoy PIN:"))
        self.txt_duress_pin = QLineEdit()
        self.txt_duress_pin.setEchoMode(QLineEdit.Password)
        self.txt_duress_pin.setPlaceholderText("e.g. 9999")
        row_pin.addWidget(self.txt_duress_pin)

        self.btn_save_pin = QPushButton("💾 Save Decoy PIN")
        self.btn_save_pin.clicked.connect(self._on_save_pin_clicked)
        row_pin.addWidget(self.btn_save_pin)
        pan_box_l.addLayout(row_pin)

        self.btn_audit_privacy = QPushButton("🛡️ Run User Privacy & Permissions Audit")
        self.btn_audit_privacy.setStyleSheet("color: #e0af68;")
        self.btn_audit_privacy.clicked.connect(self._on_audit_clicked)
        pan_box_l.addWidget(self.btn_audit_privacy)

        tpan_layout.addWidget(pan_box)
        tpan_layout.addStretch()
        self.tabs.addTab(tab_panic, "🚨 Panic Mode")

        # Tab 4: BLE Proximity (Feature 7)
        tab_ble = QWidget()
        tb_layout = QVBoxLayout(tab_ble)
        tb_layout.setSpacing(10)

        lbl_ble_desc = QLabel(
            "Measures Bluetooth Low Energy (BLE) RSSI signal strength from your paired smartwatch or smartphone "
            "to show proximity radar status on the login screen."
        )
        lbl_ble_desc.setWordWrap(True)
        lbl_ble_desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        tb_layout.addWidget(lbl_ble_desc)

        ble_box = QGroupBox("Bluetooth Device Proximity")
        ble_box_l = QVBoxLayout(ble_box)

        self.lbl_ble_status = QLabel("Bluetooth Scanner: Ready")
        ble_box_l.addWidget(self.lbl_ble_status)

        paired_devices = BLEProximityManager.list_paired_devices()
        dev_str = ", ".join([d.name for d in paired_devices]) if paired_devices else "None detected (pair phone via BlueZ)"
        self.lbl_paired = QLabel(f"Paired Devices: {dev_str}")
        self.lbl_paired.setStyleSheet("color: #7aa2f7;")
        ble_box_l.addWidget(self.lbl_paired)

        tb_layout.addWidget(ble_box)
        tb_layout.addStretch()
        self.tabs.addTab(tab_ble, "📶 BLE Proximity")

        layout.addWidget(self.tabs)

        # Footer
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def refresh_all_status(self):
        # Start Passkey HTTP server if not running
        PasskeyAuthServer.start_http_server(port=8089)
        self.refresh_fido_status()

    def refresh_fido_status(self):
        status = FIDO2Detector.get_primary_token_status()
        if status.get("detected"):
            self.lbl_fido_status.setText(f"✅ {status['vendor_name']} Connected ({status['state']})")
            self.lbl_fido_status.setStyleSheet("color: #4ade80; font-weight: bold; font-size: 13px;")
        else:
            self.lbl_fido_status.setText("ℹ️ No USB security key currently connected.")
            self.lbl_fido_status.setStyleSheet("color: #94a3b8; font-size: 13px;")

    def _on_test_passkey_clicked(self):
        session = PasskeyAuthServer.create_session("prajithj")
        url = f"http://localhost:8089/auth/{session.session_id}"
        webbrowser.open(url)

    def _on_save_pin_clicked(self):
        pin = self.txt_duress_pin.text().strip()
        if not pin:
            QMessageBox.warning(self, "Invalid PIN", "Please enter a non-empty decoy PIN.")
            return

        pin_hash, salt = PanicModeManager.hash_duress_pin(pin)
        conf = PanicModeConfig(
            enabled=True,
            decoy_username="guest",
            duress_pin_hash=pin_hash,
            salt=salt,
            isolate_home_dir=True,
            silent_alert_cmd="",
        )
        PanicModeManager.save_config(conf)
        self.txt_duress_pin.clear()
        QMessageBox.information(self, "Decoy PIN Saved", "✅ Panic mode decoy PIN configured successfully!")

    def _on_audit_clicked(self):
        audit = PanicModeManager.run_privacy_audit()
        if audit.get("safe"):
            QMessageBox.information(self, "Privacy Audit Passed", "✅ All home directory permissions (0700) are securely configured.")
        else:
            issues = "\n".join(audit.get("issues", []))
            QMessageBox.warning(self, "Privacy Issues Detected", f"⚠️ Found permission issues:\n{issues}")
