"""
SDDM Theme Manager UI Package
"""

from .archive_installer import ArchiveInstaller
from .detail_panel import DetailPanel
from .install_dialog import InstallDialog
from .live_console import LiveConsoleDrawer
from .main_window import MainWindow
from .preview_overlay import PreviewExitOverlay
from .store_dialog import StoreDialog
from .theme_editor import (
    CodeEditor,
    INISyntaxHighlighter,
    LineNumberArea,
    QMLSyntaxHighlighter,
    ThemeEditor,
)
from .theme_grid import ThemeCard, ThemeGridWidget
from .theme_tutorial_dialog import (
    TEMPLATE_MODES_TUTORIAL_DATA,
    THEME_FILES_TUTORIAL_DATA,
    ThemeTutorialDialog,
)
from .theme_writer import ThemeWriter

__all__ = [
    "MainWindow",
    "ThemeGridWidget",
    "ThemeCard",
    "DetailPanel",
    "StoreDialog",
    "PreviewExitOverlay",
    "InstallDialog",
    "LiveConsoleDrawer",
    "ThemeEditor",
    "CodeEditor",
    "LineNumberArea",
    "INISyntaxHighlighter",
    "QMLSyntaxHighlighter",
    "ThemeWriter",
    "ArchiveInstaller",
    "ThemeTutorialDialog",
    "THEME_FILES_TUTORIAL_DATA",
    "TEMPLATE_MODES_TUTORIAL_DATA",
]
