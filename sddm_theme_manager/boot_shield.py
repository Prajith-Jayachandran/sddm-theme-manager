"""
Shim to expose core.boot_shield under the sddm_theme_manager package namespace.
"""

from core.boot_shield import BootShield, SHIELD_SERVICE_PATH, SHIELD_SCRIPT_PATH, SHIELD_LOG_PATH

__all__ = ["BootShield", "SHIELD_SERVICE_PATH", "SHIELD_SCRIPT_PATH", "SHIELD_LOG_PATH"]
