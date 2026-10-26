"""
SDDM Theme Manager - Bluetooth BLE Proximity Auto-Unlock (Feature 7)
Monitors Bluetooth Low Energy (BLE) RSSI signal strength from paired smartwatches/smartphones
and triggers proximity-based auto-unlock when within range (e.g. < 1 meter).
"""

import json
import math
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

BLE_CONFIG_PATH = Path.home() / ".config/sddm-theme-manager/ble_proximity.json"


@dataclass
class PairedBLEDevice:
    mac_address: str
    name: str
    rssi: Optional[int] = None
    distance_meters: Optional[float] = None
    in_range: bool = False


class BLEProximityManager:
    """Manages Bluetooth device discovery, signal strength telemetry, and auto-unlock thresholds."""

    DEFAULT_TX_POWER = -59  # Measured power at 1 meter
    PATH_LOSS_EXPONENT = 2.0  # Free space / indoor path loss
    DEFAULT_UNLOCK_THRESHOLD_METERS = 1.2

    @classmethod
    def rssi_to_distance(cls, rssi: int, tx_power: int = -59, n: float = 2.0) -> float:
        """
        Calculate approximate distance in meters using Log-Distance Path Loss Model.
        """
        if rssi >= 0:
            return 0.1
        ratio = (tx_power - rssi) / (10.0 * n)
        distance = math.pow(10.0, ratio)
        return round(max(0.1, distance), 2)

    @classmethod
    def list_paired_devices(cls) -> List[PairedBLEDevice]:
        """Query bluetoothctl for paired Bluetooth devices."""
        devices = []
        if not shutil.which("bluetoothctl"):
            return [
                PairedBLEDevice(mac_address="AA:BB:CC:DD:EE:01", name="Smartwatch Ultra (Simulated)"),
                PairedBLEDevice(mac_address="AA:BB:CC:DD:EE:02", name="Galaxy Pixel (Simulated)"),
            ]

        try:
            res = subprocess.run(["bluetoothctl", "paired-devices"], capture_output=True, text=True, timeout=3)
            for line in res.stdout.splitlines():
                # Format: Device AA:BB:CC:DD:EE:FF DeviceName
                parts = line.strip().split(maxsplit=2)
                if len(parts) >= 3 and parts[0] == "Device":
                    devices.append(PairedBLEDevice(mac_address=parts[1], name=parts[2]))
        except Exception:
            pass

        return devices

    @classmethod
    def read_device_rssi(cls, mac_address: str) -> Optional[int]:
        """Read current RSSI for connected/advertising device via bluetoothctl."""
        if not shutil.which("bluetoothctl"):
            return -58  # Simulated strong signal

        try:
            res = subprocess.run(["bluetoothctl", "info", mac_address], capture_output=True, text=True, timeout=2)
            for line in res.stdout.splitlines():
                if "RSSI:" in line:
                    val = line.split("RSSI:")[1].split()[0]
                    return int(val)
        except Exception:
            pass

        return -62

    @classmethod
    def check_proximity_status(cls) -> Dict:
        """Evaluate proximity for configured target device."""
        conf = cls.load_config()
        target_mac = conf.get("target_mac", "")
        threshold = conf.get("threshold_meters", cls.DEFAULT_UNLOCK_THRESHOLD_METERS)
        enabled = conf.get("enabled", False)

        if not target_mac:
            return {
                "enabled": enabled,
                "configured": False,
                "target_mac": "",
                "in_range": False,
                "distance": None,
                "rssi": None,
            }

        rssi = cls.read_device_rssi(target_mac) or -99
        dist = cls.rssi_to_distance(rssi)
        in_range = dist <= threshold if enabled else False

        return {
            "enabled": enabled,
            "configured": True,
            "target_mac": target_mac,
            "rssi": rssi,
            "distance": dist,
            "in_range": in_range,
        }

    @classmethod
    def load_config(cls) -> dict:
        if BLE_CONFIG_PATH.exists():
            try:
                return json.loads(BLE_CONFIG_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"enabled": False, "target_mac": "", "threshold_meters": cls.DEFAULT_UNLOCK_THRESHOLD_METERS}

    @classmethod
    def save_config(cls, conf: dict):
        BLE_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        BLE_CONFIG_PATH.write_text(json.dumps(conf, indent=2), encoding="utf-8")

    @classmethod
    def generate_indicator_qml(cls) -> str:
        """Generates dynamic Bluetooth proximity indicator QML widget."""
        return """import QtQuick 2.15

Rectangle {
    id: bleRadarRoot
    width: 200
    height: 38
    radius: 19
    color: Qt.rgba(0.08, 0.10, 0.16, 0.8)
    border.color: inRange ? "#22c55e" : "#3b82f6"
    border.width: 1

    property bool inRange: false
    property string deviceName: "Smartwatch"
    property real distance: 0.8

    Row {
        anchors.centerIn: parent
        spacing: 8

        Text {
            text: bleRadarRoot.inRange ? "🔓" : "📶"
            font.pixelSize: 15
            verticalAlignment: Text.AlignVCenter
        }

        Text {
            text: bleRadarRoot.inRange ? "Proximity Ready (" + bleRadarRoot.distance + "m)" : "Searching BLE…"
            color: bleRadarRoot.inRange ? "#4ade80" : "#93c5fd"
            font.pixelSize: 12
            font.bold: true
            verticalAlignment: Text.AlignVCenter
        }
    }
}
"""
