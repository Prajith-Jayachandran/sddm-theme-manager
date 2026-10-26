"""
SDDM Theme Manager - Theme Files & Template Modes Tutorial Dialog
Interactive walkthrough explaining the role, syntax, and importance of each file
in an SDDM theme folder, as well as the creation template modes (Minimal, Custom, Boilerplate).
Features exact 60-word descriptions and step-by-step Next/Previous slide navigation.
"""

from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# Detailed specifications for standard SDDM theme files (60 words each)
THEME_FILES_TUTORIAL_DATA: List[Dict[str, str]] = [
    {
        "filename": "Main.qml",
        "title": "Main.qml — Primary Greeter Interface",
        "icon": "🧩",
        "badge": "Core Greeter UI Script (Mandatory)",
        "badge_color": "#7aa2f7",
        "role": "Critical: Primary graphical and logical entry point executed by SDDM.",
        "description": (
            "Main.qml serves as the primary visual and functional entry point for any SDDM theme. "
            "Written in QtQuick and QML, it renders the entire greeter interface—including background "
            "wallpapers, user avatars, session pickers, password input boxes, and power buttons. "
            "It interfaces directly with SDDM daemon global objects like sddm, userModel, and sessionModel "
            "to authenticate user logins and handle system power actions reliably."
        ),
        "syntax": "Qt 6 / QtQuick / SddmComponents 2.0",
        "example": (
            "import QtQuick\n"
            "import SddmComponents 2.0\n\n"
            "Rectangle {\n"
            "    width: Screen.width; height: Screen.height\n"
            "    // Renders background, clock, user cards, and password input\n"
            "    Image { source: config.background }\n"
            "    Connections {\n"
            "        target: sddm\n"
            "        function onLoginFailed() { errorText.text = 'Failed'; }\n"
            "    }\n"
            "}"
        ),
    },
    {
        "filename": "theme.conf",
        "title": "theme.conf — Master Visual Configuration",
        "icon": "📄",
        "badge": "Central Configuration (INI Format)",
        "badge_color": "#a6e3a1",
        "role": "Essential: Defines default visual parameters parsed into the QML config object.",
        "description": (
            "The theme.conf file is the master configuration file governing the visual appearance of an "
            "SDDM theme. Structured in standard INI format under the [General] section, it declares customizable "
            "properties such as wallpaper filenames, primary fonts, sizes, colors, and clock formats. "
            "The SDDM greeter loads these settings into the QML config context property, decoupling styling "
            "values cleanly from underlying QML code."
        ),
        "syntax": "INI Configuration format",
        "example": (
            "[General]\n"
            "background=background.png\n"
            "type=image\n"
            "font=Sans\n"
            "fontSize=11\n"
            "color=#c0caf5\n"
            "accentColor=#7aa2f7\n"
            "clockFormat=24h\n"
            "showClock=true"
        ),
    },
    {
        "filename": "theme.conf.user",
        "title": "theme.conf.user — Non-Destructive User Overrides",
        "icon": "⚙️",
        "badge": "User Preferences Layer (INI Format)",
        "badge_color": "#fab387",
        "role": "Important: Safely overrides theme.conf settings without modifying package files.",
        "description": (
            "The theme.conf.user file provides a non-destructive user override layer placed directly alongside "
            "theme.conf in the theme directory. Whenever users customize settings—such as picking a different "
            "wallpaper, custom accent colors, or blur levels—overrides are written here. SDDM automatically merges "
            "this file over theme.conf, ensuring personal visual adjustments persist safely across system package "
            "updates without breaking original theme defaults at all times."
        ),
        "syntax": "INI Configuration format (User overrides)",
        "example": (
            "[General]\n"
            "# Custom background override without modifying system theme.conf\n"
            "background=/home/user/Pictures/custom_wallpaper.png\n"
            "accentColor=#bb9af7\n"
            "blurRadius=15"
        ),
    },
    {
        "filename": "metadata.desktop",
        "title": "metadata.desktop — SDDM Greeter Specification",
        "icon": "🖥️",
        "badge": "Desktop Entry Specification (Mandatory)",
        "badge_color": "#cba6f7",
        "role": "Mandatory: Required by SDDM display manager to discover and load the theme.",
        "description": (
            "The metadata.desktop file is the mandatory desktop entry specification required by SDDM to register "
            "and display a theme. It defines critical greeter attributes including theme name, description, author, "
            "version, Type=sddm-theme, and QtVersion=6. Crucially, it tells the display manager which QML script to launch "
            "via MainScript=Main.qml and which configuration to parse via ConfigFile=theme.conf. Without it, SDDM cannot load the theme properly."
        ),
        "syntax": "FreeDesktop .desktop INI specification",
        "example": (
            "[SddmGreeterTheme]\n"
            "Name=MyCustomTheme\n"
            "Description=Modern Dark SDDM Theme\n"
            "Author=Custom\n"
            "Type=sddm-theme\n"
            "Version=1.0\n"
            "MainScript=Main.qml\n"
            "ConfigFile=theme.conf\n"
            "QtVersion=6"
        ),
    },
    {
        "filename": "metadata.json",
        "title": "metadata.json — Modern Theme Package Manifest",
        "icon": "📋",
        "badge": "Package & Store Manifest (JSON Format)",
        "badge_color": "#89dceb",
        "role": "Recommended: Machine-readable metadata used by theme managers and package installers.",
        "description": (
            "The metadata.json file provides modern machine-readable JSON metadata for theme managers, store browsers, "
            "and packaging tools. Containing structured keys for name, author, version, description, license, and repository "
            "URLs, it enables desktop tools to catalog, inspect, and safely validate theme packages. Unlike legacy desktop files, "
            "this standardized JSON format simplifies external indexing, dependency checking, and automated theme updates across "
            "desktop environments."
        ),
        "syntax": "JSON Data Format",
        "example": (
            "{\n"
            '  "name": "MyCustomTheme",\n'
            '  "author": "Custom",\n'
            '  "version": "1.0",\n'
            '  "description": "Modern SDDM Qt 6 theme",\n'
            '  "license": "MIT"\n'
            "}"
        ),
    },
    {
        "filename": "background.png",
        "title": "background.png — Greeter Wallpaper / Backdrop",
        "icon": "🖼️",
        "badge": "Default Visual Asset (PNG/JPG/Video)",
        "badge_color": "#f9e2af",
        "role": "Visual: The default backdrop asset rendered behind authentication controls.",
        "description": (
            "The background.png file supplies the primary high-resolution visual backdrop rendered behind all login "
            "cards and controls in the greeter. Typically formatted as a 1920×1080 or 4K PNG or JPG image, it establishes "
            "the core aesthetic mood. Modern themes reference this asset inside theme.conf via background=background.png, "
            "and can dynamically replace it with alternative images or video loops without modifying QML layouts."
        ),
        "syntax": "Raster image (1920×1080+ PNG/JPG) or animated video (.mp4)",
        "example": (
            "# In theme.conf:\n"
            "[General]\n"
            "background=background.png\n"
            "type=image   # or type=video"
        ),
    },
    {
        "filename": "preview.png",
        "title": "preview.png — Thumbnail Screenshot",
        "icon": "👁️",
        "badge": "Theme Selector Thumbnail (640×360)",
        "badge_color": "#f38ba8",
        "role": "Visual: Showcased in theme selector grids and system settings managers.",
        "description": (
            "The preview.png file is the thumbnail screenshot displayed within theme managers, KDE System Settings, "
            "and SDDM configuration dialogs. Sized typically at 640×360 or 800×450 pixels, it presents an accurate preview "
            "of how the login screen appears when active. Having a crisp preview image allows users to visually browse and "
            "identify themes in manager grids before activating them on their systems."
        ),
        "syntax": "Raster image (640×360 or 800×450 PNG)",
        "example": (
            "# Placed directly in theme directory:\n"
            "/usr/share/sddm/themes/<name>/preview.png\n"
            "# Picked up automatically by SDDM Theme Manager grid"
        ),
    },
    {
        "filename": "Components/",
        "title": "Components/ — Modular QML UI Sub-components",
        "icon": "📁",
        "badge": "Modular Component Subdirectory",
        "badge_color": "#eba0ac",
        "role": "Structural: Organizes modular interface elements (Clock, Avatar, SessionPanel).",
        "description": (
            "The Components folder contains auxiliary modular QML files that break down complex theme interfaces into "
            "clean, maintainable building blocks. Production themes encapsulate distinct elements—such as Clock.qml, "
            "SessionPanel.qml, AvatarMask.qml, or PowerButtons.qml—inside this directory. Importing these modular components "
            "into Main.qml keeps the main script organized, simplifies visual customization, and prevents bugs when enhancing "
            "individual widgets or animation effects in login screen themes."
        ),
        "syntax": "Directory containing reusable *.qml component files",
        "example": (
            "Components/\n"
            "├── Clock.qml        # Digital or analog time display\n"
            "├── SessionPanel.qml # Wayland/X11 session picker\n"
            "├── UserAvatar.qml   # Masked profile icon\n"
            "└── PowerMenu.qml    # Reboot / Shutdown actions"
        ),
    },
]

# Detailed specifications for Theme Creation Template Modes (60 words each)
TEMPLATE_MODES_TUTORIAL_DATA: List[Dict[str, str]] = [
    {
        "id": "minimal",
        "filename": "Minimal Code Mode",
        "title": "Minimal Code Mode — 100% Asset-Free",
        "icon": "🧼",
        "badge": "Recommended for Custom Themes",
        "badge_color": "#a6e3a1",
        "role": "Asset-Free: Scaffolds strictly code and configs with procedural fallback.",
        "description": (
            "The Minimal Code mode scaffolds an ultra-clean theme directory containing strictly "
            "essential code and configuration files without generating any dummy binary images. "
            "Main.qml features a built-in procedural dark gradient fallback, guaranteeing the greeter "
            "loads cleanly with zero errors. This mode is ideal for developers who want a lightweight "
            "foundation without needing to manually delete unwanted starter image assets at all."
        ),
        "syntax": "Clean Directory: Main.qml, theme.conf, metadata.desktop, metadata.json",
        "example": (
            "# In theme.conf:\n"
            "[General]\n"
            "background=\n"
            "type=color\n"
            "color=#1a1b26\n\n"
            "// Main.qml renders a sleek procedural\n"
            "// dark gradient with zero missing-image warnings."
        ),
    },
    {
        "id": "custom",
        "filename": "Custom Wallpaper Mode",
        "title": "Custom Wallpaper Mode — Direct Import",
        "icon": "🖼️",
        "badge": "Direct Asset Provisioning",
        "badge_color": "#7aa2f7",
        "role": "Personalized: Copies your chosen wallpaper and generates matching preview.",
        "description": (
            "The Custom Wallpaper mode streamlines theme creation by prompting you to select your own "
            "high-resolution wallpaper image right at the start. It automatically imports your chosen "
            "file into the theme directory, sets the background key in theme.conf, and generates an "
            "accurate preview thumbnail. This eliminates repetitive manual asset copying and lets you "
            "preview your personalized theme instantly on your desktop."
        ),
        "syntax": "Imports selected image as background.<ext> + generates preview.png",
        "example": (
            "# Selected: /home/user/Pictures/wallpaper.jpg\n"
            "# Theme Output:\n"
            "├── background.jpg   # Your exact chosen image\n"
            "├── preview.png      # Scaled 640x360 thumbnail\n"
            "└── theme.conf       # background=background.jpg"
        ),
    },
    {
        "id": "boilerplate",
        "filename": "Boilerplate Starter Mode",
        "title": "Boilerplate Starter Mode — Sample Assets",
        "icon": "🎨",
        "badge": "Full Sample Boilerplate",
        "badge_color": "#fab387",
        "role": "Starter Kit: Includes synthetic 1080p sample wallpaper and preview.",
        "description": (
            "The Boilerplate Starter mode provisions a comprehensive starter package complete with "
            "synthetic 1920×1080 background wallpaper and preview thumbnail assets. It configures "
            "theme.conf with full visual defaults, serving as a ready-to-test blueprint for experimenting "
            "with SDDM styling. This mode is best suited for beginners who want an immediately testable "
            "login screen before substituting custom graphics or layouts later on production systems."
        ),
        "syntax": "Complete boilerplate: code + starter background.png + preview.png",
        "example": (
            "# Theme Directory:\n"
            "├── background.png   # 1920x1080 generated dark gradient\n"
            "├── preview.png      # 640x360 scaled thumbnail\n"
            "├── Main.qml         # Full greeter script\n"
            "└── theme.conf       # Pre-configured visual defaults"
        ),
    },
    {
        "id": "hybrid",
        "filename": "Hybrid Asset Control",
        "title": "Hybrid Asset Control — Granular Switches",
        "icon": "⚙️",
        "badge": "Granular Asset Switches",
        "badge_color": "#cba6f7",
        "role": "Flexible: Independent control over preview thumbnails and user overrides.",
        "description": (
            "The Hybrid Asset Control system grants granular flexibility during theme scaffolding "
            "through optional thumbnail toggles and non-destructive configuration overrides. Whether "
            "building a minimal code-only theme or importing custom artwork, you can toggle thumbnail "
            "generation independently. This ensures your theme directory matches your exact workflow "
            "preferences while maintaining full compatibility with SDDM system managers and greeter "
            "preview tools across Linux desktops."
        ),
        "syntax": "Toggle: [ ] Generate preview.png thumbnail (independent switch)",
        "example": (
            "# Minimal mode with preview option enabled:\n"
            "├── Main.qml         # Procedural fallback\n"
            "├── theme.conf       # background=\n"
            "└── preview.png      # Lightweight card thumbnail only\n"
            "# No bulky 1080p background.png dummy file created!"
        ),
    },
]


class ThemeTutorialDialog(QDialog):
    """
    Interactive tutorial dialog for SDDM theme files and creation template modes.
    Allows navigating through all items with [Previous] and [Next] buttons.
    Each item features an exact 60-word description of its role and importance.
    """

    file_open_requested = Signal(str)

    def __init__(self, theme_path: Optional[Path | str] = None, parent=None, initial_category: str = "files"):
        super().__init__(parent)
        self.theme_path = Path(theme_path).resolve() if theme_path else None
        self.current_category = initial_category if initial_category in ("files", "modes") else "files"
        self.current_index = 0

        self.setWindowTitle("SDDM Theme Tutorial & Architecture Guide")
        self.resize(780, 530)
        self.setMinimumSize(660, 450)
        self.setModal(True)

        self.setStyleSheet(
            "QDialog {"
            "  background-color: #1a1b26;"
            "  color: #c0caf5;"
            "}"
            "QLabel {"
            "  color: #c0caf5;"
            "}"
            "QListWidget {"
            "  background-color: #16161e;"
            "  border: 1px solid #3b4261;"
            "  border-radius: 8px;"
            "  color: #c0caf5;"
            "  padding: 4px;"
            "}"
            "QListWidget::item {"
            "  padding: 8px 10px;"
            "  border-radius: 6px;"
            "  margin: 2px 0px;"
            "}"
            "QListWidget::item:hover {"
            "  background-color: #24283b;"
            "  color: #ffffff;"
            "}"
            "QListWidget::item:selected {"
            "  background-color: #3d59a1;"
            "  color: #ffffff;"
            "  font-weight: bold;"
            "}"
            "QPushButton, QToolButton {"
            "  background-color: #24283b;"
            "  color: #c0caf5;"
            "  border: 1px solid #3b4261;"
            "  border-radius: 6px;"
            "  padding: 7px 16px;"
            "  font-weight: 500;"
            "}"
            "QPushButton:hover, QToolButton:hover {"
            "  background-color: #2f354f;"
            "  border-color: #7aa2f7;"
            "  color: #ffffff;"
            "}"
            "QPushButton#categoryActiveBtn {"
            "  background-color: #3d59a1;"
            "  color: #ffffff;"
            "  border: 1px solid #7aa2f7;"
            "  font-weight: 600;"
            "}"
            "QPushButton#navNextBtn {"
            "  background-color: #3d59a1;"
            "  color: #ffffff;"
            "  border: 1px solid #7aa2f7;"
            "  font-weight: 600;"
            "}"
            "QPushButton#navNextBtn:hover {"
            "  background-color: #7aa2f7;"
            "  color: #1a1b26;"
            "}"
            "QPushButton:disabled {"
            "  background-color: #1f2335;"
            "  color: #565f89;"
            "  border-color: #292e42;"
            "}"
        )

        self._build_ui()
        self._setup_shortcuts()
        self.load_category(self.current_category)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header Title & Category Switcher
        header_layout = QHBoxLayout()
        header_left = QVBoxLayout()
        header_left.setSpacing(2)

        self.lbl_header_title = QLabel("📖 SDDM Theme Tutorial & Architecture Guide", self)
        self.lbl_header_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        header_left.addWidget(self.lbl_header_title)

        self.lbl_header_sub = QLabel(
            "Explore the purpose, syntax, and importance of every file and creation template mode.", self
        )
        self.lbl_header_sub.setStyleSheet("font-size: 12px; color: #9aa5ce;")
        header_left.addWidget(self.lbl_header_sub)
        header_layout.addLayout(header_left)
        header_layout.addStretch()

        # Category Buttons (Theme Files vs. Creation Modes)
        cat_box = QHBoxLayout()
        cat_box.setSpacing(6)

        self.btn_cat_files = QPushButton("📄 Theme Files (8)", self)
        self.btn_cat_files.setCursor(Qt.PointingHandCursor)
        self.btn_cat_files.clicked.connect(lambda: self.load_category("files"))
        cat_box.addWidget(self.btn_cat_files)

        self.btn_cat_modes = QPushButton("🛠️ Template Modes (4)", self)
        self.btn_cat_modes.setCursor(Qt.PointingHandCursor)
        self.btn_cat_modes.clicked.connect(lambda: self.load_category("modes"))
        cat_box.addWidget(self.btn_cat_modes)

        header_layout.addLayout(cat_box)
        main_layout.addLayout(header_layout)

        # Main splitter (Left: list selector, Right: detailed info card)
        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setStyleSheet("QSplitter::handle { background-color: #24283b; width: 4px; }")

        # Left: Items List
        left_widget = QWidget(self)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        self.lbl_nav_title = QLabel("<b>Items:</b>", left_widget)
        self.lbl_nav_title.setStyleSheet("color: #7aa2f7; font-size: 12px;")
        left_layout.addWidget(self.lbl_nav_title)

        self.list_items = QListWidget(left_widget)
        self.list_items.setCursor(Qt.PointingHandCursor)
        self.list_items.currentRowChanged.connect(self._on_list_selection_changed)
        left_layout.addWidget(self.list_items, 1)

        splitter.addWidget(left_widget)

        # Right: Item Description Card
        right_widget = QWidget(self)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(10)

        # Card container
        self.card_frame = QFrame(right_widget)
        self.card_frame.setStyleSheet(
            "QFrame {"
            "  background-color: #16161e;"
            "  border: 1px solid #3b4261;"
            "  border-radius: 10px;"
            "}"
        )
        card_layout = QVBoxLayout(self.card_frame)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(12)

        # Title and Badge row
        title_row = QHBoxLayout()
        title_row.setSpacing(10)

        self.lbl_card_title = QLabel("Item Title", self.card_frame)
        self.lbl_card_title.setStyleSheet(
            "font-size: 17px; font-weight: bold; color: #ffffff; background: transparent;"
        )
        title_row.addWidget(self.lbl_card_title)

        title_row.addStretch()

        self.lbl_badge = QLabel("Badge", self.card_frame)
        self.lbl_badge.setStyleSheet(
            "QLabel {"
            "  background-color: #24283b;"
            "  color: #7aa2f7;"
            "  border: 1px solid #7aa2f7;"
            "  border-radius: 6px;"
            "  padding: 3px 10px;"
            "  font-size: 11px;"
            "  font-weight: bold;"
            "}"
        )
        title_row.addWidget(self.lbl_badge)
        card_layout.addLayout(title_row)

        # Role Callout Banner
        self.lbl_importance = QLabel("Role summary", self.card_frame)
        self.lbl_importance.setWordWrap(True)
        self.lbl_importance.setStyleSheet(
            "QLabel {"
            "  background-color: #1f2335;"
            "  color: #e0af68;"
            "  border-left: 3px solid #e0af68;"
            "  border-radius: 4px;"
            "  padding: 8px 12px;"
            "  font-size: 12px;"
            "  font-weight: 500;"
            "}"
        )
        card_layout.addWidget(self.lbl_importance)

        # Description Heading & 60-Word Description Text
        self.lbl_desc_heading = QLabel("<b>Description & Purpose:</b>", self.card_frame)
        self.lbl_desc_heading.setStyleSheet("font-size: 12px; color: #7aa2f7; background: transparent;")
        card_layout.addWidget(self.lbl_desc_heading)

        self.lbl_description = QLabel(self.card_frame)
        self.lbl_description.setWordWrap(True)
        self.lbl_description.setStyleSheet(
            "QLabel {"
            "  font-size: 13px;"
            "  color: #c0caf5;"
            "  line-height: 1.5;"
            "  background: transparent;"
            "}"
        )
        card_layout.addWidget(self.lbl_description)

        # Code Example / Structure Preview
        self.lbl_code_heading = QLabel("<b>Syntax & Example Snippet:</b>", self.card_frame)
        self.lbl_code_heading.setStyleSheet("font-size: 12px; color: #9aa5ce; background: transparent;")
        card_layout.addWidget(self.lbl_code_heading)

        self.txt_example = QTextEdit(self.card_frame)
        self.txt_example.setReadOnly(True)
        self.txt_example.setStyleSheet(
            "QTextEdit {"
            "  background-color: #1e1e2e;"
            "  color: #a6e3a1;"
            "  font-family: monospace;"
            "  font-size: 11px;"
            "  border: 1px solid #313244;"
            "  border-radius: 6px;"
            "  padding: 6px;"
            "}"
        )
        self.txt_example.setMaximumHeight(120)
        card_layout.addWidget(self.txt_example, 1)

        # Presence status tag
        self.lbl_status = QLabel("", self.card_frame)
        self.lbl_status.setStyleSheet("font-size: 11px; color: #565f89; background: transparent;")
        card_layout.addWidget(self.lbl_status)

        right_layout.addWidget(self.card_frame, 1)
        splitter.addWidget(right_widget)

        splitter.setSizes([220, 520])
        main_layout.addWidget(splitter, 1)

        # Bottom Navigation & Action Bar
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(10)

        self.btn_open_editor = QPushButton("✏️ Open in Editor", self)
        self.btn_open_editor.setToolTip("Open and view this file in Theme Editor")
        self.btn_open_editor.clicked.connect(self._on_open_file_clicked)
        bottom_bar.addWidget(self.btn_open_editor)

        bottom_bar.addStretch()

        self.btn_prev = QPushButton("◀ Previous", self)
        self.btn_prev.setToolTip("Go to previous slide (Left Arrow)")
        self.btn_prev.clicked.connect(self.go_previous)
        bottom_bar.addWidget(self.btn_prev)

        self.lbl_counter = QLabel("1 of 8", self)
        self.lbl_counter.setStyleSheet("font-size: 12px; font-weight: bold; color: #9aa5ce; padding: 0 8px;")
        bottom_bar.addWidget(self.lbl_counter)

        self.btn_next = QPushButton("Next ▶", self)
        self.btn_next.setObjectName("navNextBtn")
        self.btn_next.setToolTip("Click to view next slide (Right Arrow / Space)")
        self.btn_next.clicked.connect(self.go_next)
        bottom_bar.addWidget(self.btn_next)

        self.btn_close = QPushButton("Close", self)
        self.btn_close.clicked.connect(self.accept)
        bottom_bar.addWidget(self.btn_close)

        main_layout.addLayout(bottom_bar)

    def _setup_shortcuts(self):
        sc_next = QShortcut(QKeySequence(Qt.Key_Right), self)
        sc_next.activated.connect(self.go_next)

        sc_space = QShortcut(QKeySequence(Qt.Key_Space), self)
        sc_space.activated.connect(self.go_next)

        sc_prev = QShortcut(QKeySequence(Qt.Key_Left), self)
        sc_prev.activated.connect(self.go_previous)

        sc_esc = QShortcut(QKeySequence("Escape"), self)
        sc_esc.activated.connect(self.accept)

    def get_active_dataset(self) -> List[Dict[str, str]]:
        return THEME_FILES_TUTORIAL_DATA if self.current_category == "files" else TEMPLATE_MODES_TUTORIAL_DATA

    def load_category(self, category: str, index: int = 0):
        """Loads and switches between Theme Files and Template Modes datasets."""
        self.current_category = category
        self.current_index = index

        # Highlight active category button
        if category == "files":
            self.btn_cat_files.setObjectName("categoryActiveBtn")
            self.btn_cat_modes.setObjectName("")
            self.lbl_nav_title.setText("<b>Theme Files:</b>")
            self.btn_open_editor.setVisible(True)
        else:
            self.btn_cat_files.setObjectName("")
            self.btn_cat_modes.setObjectName("categoryActiveBtn")
            self.lbl_nav_title.setText("<b>Template Modes:</b>")
            self.btn_open_editor.setVisible(False)

        self.btn_cat_files.style().unpolish(self.btn_cat_files)
        self.btn_cat_files.style().polish(self.btn_cat_files)
        self.btn_cat_modes.style().unpolish(self.btn_cat_modes)
        self.btn_cat_modes.style().polish(self.btn_cat_modes)

        # Repopulate items list
        dataset = self.get_active_dataset()
        self.list_items.blockSignals(True)
        self.list_items.clear()
        for entry in dataset:
            item = QListWidgetItem(f"{entry['icon']} {entry['filename']}")
            self.list_items.addItem(item)
        self.list_items.setCurrentRow(self.current_index)
        self.list_items.blockSignals(False)

        self.update_slide()

    def set_current_index(self, index: int):
        dataset = self.get_active_dataset()
        if 0 <= index < len(dataset):
            self.current_index = index
            self.update_slide()

    def go_next(self):
        """Advances to the next slide or wraps to the beginning."""
        dataset = self.get_active_dataset()
        if self.current_index < len(dataset) - 1:
            self.current_index += 1
            self.update_slide()
        else:
            self.current_index = 0
            self.update_slide()

    def go_previous(self):
        """Moves back to the previous slide."""
        if self.current_index > 0:
            self.current_index -= 1
            self.update_slide()

    def _on_list_selection_changed(self, row: int):
        dataset = self.get_active_dataset()
        if 0 <= row < len(dataset):
            self.current_index = row
            self.update_slide(sync_list=False)

    def update_slide(self, sync_list: bool = True):
        """Refreshes UI elements to display the active tutorial slide."""
        dataset = self.get_active_dataset()
        data = dataset[self.current_index]
        total = len(dataset)

        prefix = "File" if self.current_category == "files" else "Mode"

        # Update card text
        self.lbl_card_title.setText(f"{data['icon']}  {data['filename']}")
        self.lbl_badge.setText(data["badge"])
        self.lbl_badge.setStyleSheet(
            f"QLabel {{ background-color: #1f2335; color: {data['badge_color']}; "
            f"border: 1px solid {data['badge_color']}; border-radius: 6px; "
            f"padding: 3px 10px; font-size: 11px; font-weight: bold; }}"
        )
        self.lbl_importance.setText(f"📌 {data['role']}")
        self.lbl_description.setText(data["description"])
        self.txt_example.setPlainText(data["example"])

        # Update counter & buttons
        self.lbl_counter.setText(f"{prefix} {self.current_index + 1} of {total}")
        self.btn_prev.setEnabled(self.current_index > 0)

        if self.current_index == total - 1:
            self.btn_next.setText("First Slide ↺")
        else:
            self.btn_next.setText("Next ▶")

        # Check file existence in theme if theme_path is available and in files category
        if self.current_category == "files":
            target_name = data["filename"].rstrip("/")
            if self.theme_path and self.theme_path.exists():
                exists = (self.theme_path / target_name).exists()
                if exists:
                    self.lbl_status.setText(f"Status in '{self.theme_path.name}':  ✅ Present on disk")
                    self.lbl_status.setStyleSheet("font-size: 11px; color: #a6e3a1; background: transparent;")
                    self.btn_open_editor.setEnabled(True)
                else:
                    self.lbl_status.setText(f"Status in '{self.theme_path.name}':  ⚠️ Not currently present")
                    self.lbl_status.setStyleSheet("font-size: 11px; color: #fab387; background: transparent;")
                    self.btn_open_editor.setEnabled(False)
            else:
                self.lbl_status.setText("Viewing standard SDDM theme specifications")
                self.lbl_status.setStyleSheet("font-size: 11px; color: #565f89; background: transparent;")
                self.btn_open_editor.setEnabled(False)
        else:
            self.lbl_status.setText("Creation Template Guide: Select this mode when scaffolding a theme")
            self.lbl_status.setStyleSheet("font-size: 11px; color: #7aa2f7; background: transparent;")

        # Synchronize list selection
        if sync_list:
            self.list_items.blockSignals(True)
            self.list_items.setCurrentRow(self.current_index)
            self.list_items.blockSignals(False)

    def _on_open_file_clicked(self):
        dataset = self.get_active_dataset()
        data = dataset[self.current_index]
        self.file_open_requested.emit(data["filename"].rstrip("/"))
        self.accept()
