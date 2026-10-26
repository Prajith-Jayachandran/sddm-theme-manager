"""
SDDM Theme Manager Core Package
"""

from .background import BackgroundManager
from .installer import ThemeInstaller
from .live_runner import LiveGreeterRunner, QMLErrorParser
from .polkit import (
    PolkitConfig,
    detect_sddm_qt_version,
    is_sddm_installed,
    remove_path_privileged,
    restart_sddm_service,
    write_file_privileged,
)
from .preview import PreviewManager
from .store_client import StoreClient, StoreItem
from .theme_applier import ThemeApplier
from .theme_scanner import Theme, ThemeScanner

__all__ = [
    "Theme",
    "ThemeScanner",
    "ThemeApplier",
    "BackgroundManager",
    "ThemeInstaller",
    "LiveGreeterRunner",
    "QMLErrorParser",
    "PreviewManager",
    "StoreClient",
    "StoreItem",
    "PolkitConfig",
    "is_sddm_installed",
    "detect_sddm_qt_version",
    "restart_sddm_service",
    "write_file_privileged",
    "remove_path_privileged",
]
