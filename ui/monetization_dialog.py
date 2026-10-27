"""
SDDM Theme Manager - Creator Monetization & Supporter Pro Pass Dialog (Feature 20)
Direct artist tip links (Ko-fi, GitHub Sponsors, Patreon) and Supporter Pro Pass management.
"""

import webbrowser
from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core.monetization import CreatorMonetizationManager
from core.theme_scanner import Theme


class MonetizationDialog(QDialog):
    """Creator Monetization & Supporter Pro Pass Modal."""

    def __init__(self, theme: Optional[Theme] = None, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setWindowTitle("⭐ Creator Support & Pro Pass")
        self.resize(520, 440)
        self.setMinimumWidth(440)
        self._setup_ui()
        self.refresh_pro_status()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        # Header Card
        header = QFrame()
        header.setStyleSheet("background-color: #1a1b26; border-radius: 8px; padding: 12px;")
        h_layout = QVBoxLayout(header)
        title = QLabel("⭐ Support Theme Creators & Pro Pass")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #e0af68;")
        h_layout.addWidget(title)

        desc = QLabel(
            "Support the open-source artists and Linux ricers who design SDDM greeters. "
            "100% of tips go directly to the theme creators via their personal sponsorship links."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #9aa5ce; font-size: 12px;")
        h_layout.addWidget(desc)
        layout.addWidget(header)

        # Theme Sponsorship Box
        sponsor_box = QGroupBox("Selected Theme Creator")
        sb_layout = QVBoxLayout(sponsor_box)

        if self.theme:
            tip_info = CreatorMonetizationManager.parse_theme_sponsorship(self.theme.path)
            self.lbl_artist = QLabel(f"🎨 Theme: {self.theme.name} (by {self.theme.author or 'Community Artist'})")
            self.lbl_artist.setStyleSheet("font-weight: bold; color: #7aa2f7;")
            sb_layout.addWidget(self.lbl_artist)

            if tip_info.has_tip_links:
                btn_tip = QPushButton(f"☕ Tip Creator on {tip_info.primary_tip_platform}")
                btn_tip.setStyleSheet(
                    "QPushButton { background-color: #ff5e5b; color: #ffffff; font-weight: bold; padding: 8px 16px; border-radius: 6px; }"
                    "QPushButton:hover { background-color: #ff7b78; }"
                )
                btn_tip.clicked.connect(lambda: webbrowser.open(tip_info.primary_tip_url))
                sb_layout.addWidget(btn_tip)
            else:
                lbl_no_tip = QLabel("This theme does not package a direct sponsorship link in metadata.desktop.")
                lbl_no_tip.setStyleSheet("color: #94a3b8; font-style: italic; font-size: 11px;")
                sb_layout.addWidget(lbl_no_tip)
        else:
            self.lbl_artist = QLabel("Select a theme in the grid to view creator donation links.")
            self.lbl_artist.setStyleSheet("color: #94a3b8; font-style: italic;")
            sb_layout.addWidget(self.lbl_artist)

        layout.addWidget(sponsor_box)

        # Supporter Pro Pass Box
        pro_box = QGroupBox("Supporter Pro Pass")
        pb_layout = QVBoxLayout(pro_box)

        self.lbl_pro_status = QLabel("Supporter Pass: Inactive")
        self.lbl_pro_status.setStyleSheet("font-weight: bold;")
        pb_layout.addWidget(self.lbl_pro_status)

        row_pass = QHBoxLayout()
        self.txt_key = QLineEdit()
        self.txt_key.setPlaceholderText("Enter Supporter Key (e.g. RICE_PRO_PASS)")
        row_pass.addWidget(self.txt_key)

        self.btn_activate_pro = QPushButton("✨ Activate Pass")
        self.btn_activate_pro.setStyleSheet("background-color: #e0af68; color: #1a1b26; font-weight: bold; border-radius: 4px; padding: 6px 12px;")
        self.btn_activate_pro.clicked.connect(self._on_activate_clicked)
        row_pass.addWidget(self.btn_activate_pro)
        pb_layout.addLayout(row_pass)

        layout.addWidget(pro_box)
        layout.addStretch()

        # Footer
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def refresh_pro_status(self):
        is_active = CreatorMonetizationManager.is_supporter_pass_active()
        if is_active:
            self.lbl_pro_status.setText("🌟 Supporter Pro Pass: Active (Unlimited AI Ricing & Themes)")
            self.lbl_pro_status.setStyleSheet("color: #4ade80; font-weight: bold;")
            self.btn_activate_pro.setText("Deactivate")
        else:
            self.lbl_pro_status.setText("Supporter Pro Pass: Standard Mode")
            self.lbl_pro_status.setStyleSheet("color: #94a3b8; font-weight: normal;")
            self.btn_activate_pro.setText("✨ Activate Pass")

    def _on_activate_clicked(self):
        is_active = CreatorMonetizationManager.is_supporter_pass_active()
        if is_active:
            CreatorMonetizationManager.set_supporter_pass(active=False)
            self.refresh_pro_status()
            QMessageBox.information(self, "Pro Pass", "Supporter Pro Pass deactivated.")
        else:
            key = self.txt_key.text().strip() or "COMMUNITY_RICE_PRO"
            CreatorMonetizationManager.set_supporter_pass(active=True, key=key)
            self.refresh_pro_status()
            QMessageBox.information(self, "Pro Pass Activated", "🎉 Thank you for supporting open-source development! Pro Pass unlocked!")
