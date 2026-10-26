"""
SDDM Theme Manager - Hot-Reload "Live Studio" for Developers (Feature 15)
Mock environment injector and file watcher for sub-30ms hot-reloads during theme development.
Simulates time of day, battery charge states, network status, and display aspect ratios.
"""

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

DEV_MOCK_ENV_PATH = Path("/tmp/sddm-dev-mock-env.json")


@dataclass
class MockEnvironmentState:
    simulated_hour: int = 12
    simulated_minute: int = 30
    simulated_battery_pct: int = 85
    simulated_is_charging: bool = False
    simulated_wifi_online: bool = True
    aspect_ratio: str = "16:9"  # "16:9", "16:10", "21:9", "9:16"
    test_user_count: int = 1


class DevReloadEnvironment:
    """Manages mock hardware states and dev sandbox parameter injection."""

    ASPECT_RATIOS = {
        "16:9": (1920, 1080),
        "16:10": (1920, 1200),
        "21:9": (2560, 1080),
        "9:16": (1080, 1920),
    }

    def __init__(self, state: Optional[MockEnvironmentState] = None):
        self.state = state or MockEnvironmentState()

    def set_time(self, hour: int, minute: int):
        self.state.simulated_hour = max(0, min(23, hour))
        self.state.simulated_minute = max(0, min(59, minute))
        self.export_state()

    def set_battery(self, pct: int, charging: bool = False):
        self.state.simulated_battery_pct = max(0, min(100, pct))
        self.state.simulated_is_charging = charging
        self.export_state()

    def set_aspect_ratio(self, ratio_key: str):
        if ratio_key in self.ASPECT_RATIOS:
            self.state.aspect_ratio = ratio_key
            self.export_state()

    def get_resolution(self) -> Tuple[int, int]:
        return self.ASPECT_RATIOS.get(self.state.aspect_ratio, (1920, 1080))

    def export_state(self):
        """Export mock state to world-readable temporary file for QML context reading."""
        try:
            payload = {
                "time": f"{self.state.simulated_hour:02d}:{self.state.simulated_minute:02d}",
                "battery_pct": self.state.simulated_battery_pct,
                "is_charging": self.state.simulated_is_charging,
                "wifi_online": self.state.simulated_wifi_online,
                "aspect_ratio": self.state.aspect_ratio,
                "resolution": self.get_resolution(),
                "user_count": self.state.test_user_count,
            }
            DEV_MOCK_ENV_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            pass

    @classmethod
    def read_mock_state(cls) -> Optional[dict]:
        if DEV_MOCK_ENV_PATH.exists():
            try:
                return json.loads(DEV_MOCK_ENV_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass
        return None
