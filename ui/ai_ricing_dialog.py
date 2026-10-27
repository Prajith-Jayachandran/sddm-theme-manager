"""
SDDM Theme Manager - Prompt-to-Theme AI Ricing Engine Dialog (Feature 16)
Translates aesthetic natural language prompts into complete, harmonious SDDM theme packages.
"""

from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core.ai_generator import AIRicingEngine


class AIRicingDialog(QDialog):
    """Prompt-to-Theme AI Ricing Studio Modal."""

    theme_generated = Signal(Path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("✨ AI Ricing Studio — Prompt to Theme")
        self.resize(520, 420)
        self.setMinimumWidth(460)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        # Header Card
        header = QFrame()
        header.setStyleSheet("background-color: #1a1b26; border-radius: 8px; padding: 12px;")
        h_layout = QVBoxLayout(header)
        title = QLabel("✨ Prompt-to-Theme AI Ricing Engine")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #bb9af7;")
        h_layout.addWidget(title)

        desc = QLabel(
            "Describe the look and vibe you want in plain English. The AI Ricing Engine analyzes "
            "mood, harmonic color theory, fonts, and geometry to generate a complete Qt6 greeter."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #9aa5ce; font-size: 12px;")
        h_layout.addWidget(desc)
        layout.addWidget(header)

        # Prompt Input Box
        box = QFrame()
        box.setStyleSheet("background-color: #16161e; border: 1px solid #292e42; border-radius: 8px; padding: 12px;")
        b_layout = QVBoxLayout(box)
        b_layout.setSpacing(8)

        lbl_prompt = QLabel("Describe your dream login theme:")
        lbl_prompt.setStyleSheet("font-weight: bold; color: #c0caf5;")
        b_layout.addWidget(lbl_prompt)

        self.txt_prompt = QLineEdit()
        self.txt_prompt.setStyleSheet("padding: 10px; font-size: 13px; background-color: #0f141c; border-radius: 6px;")
        self.txt_prompt.setPlaceholderText("e.g. Nordic arctic ice frost minimalist with glowing neon cyan clock")
        b_layout.addWidget(self.txt_prompt)

        # Preset Inspiration Chips
        chips_layout = QHBoxLayout()
        chips_layout.setSpacing(6)
        chips = [
            ("🌆 Synthwave", "Synthwave retro sunset with glowing neon clock"),
            ("❄️ Nordic Frost", "Nordic arctic ice frost minimalist"),
            ("⚡ Cyberpunk", "Cyberpunk high tech netrunner with matrix grid"),
            ("🌸 Sakura Pastel", "Sakura blossom soft pastel aesthetic"),
        ]
        for label, ptext in chips:
            btn_chip = QPushButton(label)
            btn_chip.setStyleSheet("background-color: #1f2335; color: #7aa2f7; border-radius: 12px; padding: 4px 10px; font-size: 11px;")
            btn_chip.setCursor(Qt.PointingHandCursor)
            btn_chip.clicked.connect(lambda _, t=ptext: self.txt_prompt.setText(t))
            chips_layout.addWidget(btn_chip)
        b_layout.addLayout(chips_layout)

        layout.addWidget(box)

        # AI Analysis Preview Card
        self.preview_card = QFrame()
        self.preview_card.setStyleSheet("background-color: #1a1b26; border-radius: 8px; padding: 10px;")
        p_layout = QVBoxLayout(self.preview_card)
        self.lbl_analysis = QLabel("Enter a prompt above to generate a customized SDDM theme.")
        self.lbl_analysis.setWordWrap(True)
        self.lbl_analysis.setStyleSheet("color: #94a3b8; font-size: 11px;")
        p_layout.addWidget(self.lbl_analysis)
        layout.addWidget(self.preview_card)

        # Action Buttons
        btn_row = QHBoxLayout()
        self.btn_generate = QPushButton("🎨 Generate & Install Theme")
        self.btn_generate.setStyleSheet(
            "QPushButton { background-color: #bb9af7; color: #1a1b26; font-weight: bold; padding: 10px 20px; border-radius: 6px; font-size: 13px; }"
            "QPushButton:hover { background-color: #cfc9ff; }"
        )
        self.btn_generate.clicked.connect(self._on_generate_clicked)
        btn_row.addWidget(self.btn_generate)

        btn_row.addStretch()

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _on_generate_clicked(self):
        prompt = self.txt_prompt.text().strip()
        if not prompt:
            QMessageBox.warning(self, "Empty Prompt", "Please enter a description for your theme.")
            return

        design = AIRicingEngine.analyze_prompt(prompt)
        theme_slug = f"ai-{design.mood.lower().replace(' ', '-')}"
        target_dir = Path.home() / f".local/share/sddm/themes/{theme_slug}"

        ok, out_path, msg = AIRicingEngine.generate_theme_package(prompt, target_dir)
        if ok and out_path:
            QMessageBox.information(
                self,
                "Theme Generated Successfully",
                f"🎉 AI Ricing Complete!\n\n"
                f"• Theme Mood: {design.mood}\n"
                f"• Accent Color: {design.accent_color}\n"
                f"• Background: {design.bg_color}\n"
                f"• Saved To: {out_path}\n\n"
                "You can now select and test it in SDDM Theme Manager!",
            )
            self.theme_generated.emit(out_path)
            self.accept()
        else:
            QMessageBox.warning(self, "Generation Error", f"Could not generate theme: {msg}")
