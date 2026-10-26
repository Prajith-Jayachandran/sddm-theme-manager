"""
SDDM Theme Manager Core Package
"""

from .ai_generator import AIRicingEngine
from .audio_chime import AudioChimeManager, AudioSynthesizer
from .background import BackgroundManager
from .ble_proximity import BLEProximityManager
from .boot_shield import BootShield
from .chameleon_presets import ChameleonPresetsManager
from .dev_reload import DevReloadEnvironment
from .fido2_detector import FIDO2Detector
from .greeter_games import GreeterGamesManager
from .installer import ThemeInstaller
from .live_runner import LiveGreeterRunner, QMLErrorParser
from .marketplace import DecentralizedMarketplace
from .monetization import CreatorMonetizationManager
from .mpris_bridge import MPRISBridge
from .panic_mode import PanicModeManager
from .passkey_server import PasskeyAuthServer
from .polkit import (
    PolkitConfig,
    detect_sddm_qt_version,
    is_sddm_installed,
    remove_path_privileged,
    restart_sddm_service,
    write_file_privileged,
)
from .preview import PreviewManager
from .session_peek import SessionPeekManager
from .shader_engine import ShaderEngine
from .solar_timelapse import SolarTimelapseManager
from .sticky_notes import StickyNotesManager
from .store_client import StoreClient, StoreItem
from .system_hud import SystemHUDTelemetry
from .theme_applier import ThemeApplier
from .theme_enhancer import ThemeEnhancer
from .theme_scanner import Theme, ThemeScanner
from .weather_service import WeatherService

__all__ = [
    "Theme",
    "ThemeScanner",
    "ThemeApplier",
    "ThemeEnhancer",
    "BackgroundManager",
    "ThemeInstaller",
    "BootShield",
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
    "ShaderEngine",
    "AudioChimeManager",
    "AudioSynthesizer",
    "WeatherService",
    "MPRISBridge",
    "SolarTimelapseManager",
    "PasskeyAuthServer",
    "BLEProximityManager",
    "PanicModeManager",
    "FIDO2Detector",
    "SystemHUDTelemetry",
    "StickyNotesManager",
    "SessionPeekManager",
    "ChameleonPresetsManager",
    "DevReloadEnvironment",
    "AIRicingEngine",
    "GreeterGamesManager",
    "DecentralizedMarketplace",
    "CreatorMonetizationManager",
]
