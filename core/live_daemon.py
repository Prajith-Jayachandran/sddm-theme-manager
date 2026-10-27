"""
SDDM Theme Manager - Live Telemetry & Command Daemon
Synchronizes real-time hardware telemetry, MPRIS playback, FIDO2 tokens,
weather, and household notes to world-readable shared files (/tmp/sddm-*.json),
and processes interactive action commands issued by the SDDM greeter QML widgets.
"""

import json
import logging
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

from .fido2_detector import FIDO2Detector
from .mpris_bridge import MPRISBridge
from .sticky_notes import StickyNotesManager
from .system_hud import SystemHUDTelemetry
from .weather_service import WeatherService

logger = logging.getLogger("sddm_theme_manager.live_daemon")

CMD_FILE = Path("/tmp/sddm-mpris-cmd.txt")
AUTH_STATUS_FILE = Path("/tmp/sddm-passkey-auth.json")


class LiveTelemetryDaemon:
    """Background synchronizer for SDDM greeter Next-Gen widgets."""

    _thread: Optional[threading.Thread] = None
    _running: bool = False
    _last_weather_fetch: float = 0.0

    @classmethod
    def process_media_commands(cls):
        """Check for and execute queued media player commands from QML widgets."""
        if CMD_FILE.exists():
            try:
                cmd = CMD_FILE.read_text(encoding="utf-8").strip()
                if cmd:
                    logger.info("Executing greeter media command: %s", cmd)
                    if cmd == "play-pause":
                        MPRISBridge.play_pause()
                    elif cmd == "next":
                        MPRISBridge.next_track()
                    elif cmd == "previous":
                        MPRISBridge.previous_track()
                    CMD_FILE.write_text("", encoding="utf-8")
            except Exception as e:
                logger.debug("Error processing media command: %s", e)

    @classmethod
    def update_telemetry(cls):
        """Update hardware telemetry snapshot in /tmp/sddm-telemetry.json."""
        try:
            SystemHUDTelemetry.snapshot_metrics()
        except Exception as e:
            logger.debug("Failed to update HUD telemetry: %s", e)

    @classmethod
    def update_mpris(cls):
        """Update active MPRIS player metadata in /tmp/sddm-mpris.json."""
        try:
            MPRISBridge.get_current_track()
        except Exception as e:
            logger.debug("Failed to update MPRIS metadata: %s", e)

    @classmethod
    def update_fido2(cls):
        """Update FIDO2 token presence in /tmp/sddm-fido2.json."""
        try:
            status = FIDO2Detector.get_primary_token_status()
            out_file = Path("/tmp/sddm-fido2.json")
            out_file.write_text(json.dumps(status, indent=2), encoding="utf-8")
            os.chmod(str(out_file), 0o666)
        except Exception as e:
            logger.debug("Failed to update FIDO2 status: %s", e)

    @classmethod
    def update_weather(cls, force: bool = False):
        """Update weather and moon phase in /tmp/sddm-weather.json."""
        now = time.time()
        # Fetch weather at most once every 15 minutes unless forced
        if force or (now - cls._last_weather_fetch > 900):
            try:
                data = WeatherService.fetch_weather(timeout=2)
                cls._last_weather_fetch = now
                out_file = Path("/tmp/sddm-weather.json")
                out_file.write_text(json.dumps(data.__dict__, indent=2), encoding="utf-8")
                os.chmod(str(out_file), 0o666)
            except Exception as e:
                logger.debug("Failed to update weather: %s", e)

    @classmethod
    def update_notes(cls):
        """Ensure household notes are synced to /tmp/sddm-sticky-notes.json."""
        try:
            notes = StickyNotesManager.load_notes()
            StickyNotesManager.save_notes(notes)
        except Exception as e:
            logger.debug("Failed to sync sticky notes: %s", e)

    @classmethod
    def update_all_once(cls):
        """1-Shot execution of all telemetry and command processing."""
        cls.process_media_commands()
        cls.update_telemetry()
        cls.update_mpris()
        cls.update_fido2()
        cls.update_weather(force=True)
        cls.update_notes()

    @classmethod
    def _run_loop(cls):
        """Internal daemon loop running at ~1 Hz."""
        cls.update_weather(force=True)
        while cls._running:
            cls.process_media_commands()
            cls.update_telemetry()
            cls.update_mpris()
            cls.update_fido2()
            cls.update_notes()
            time.sleep(1.5)

    @classmethod
    def start(cls):
        """Start the live background daemon thread if not already running."""
        if cls._running:
            return
        cls._running = True
        cls._thread = threading.Thread(target=cls._run_loop, daemon=True, name="SDDM-LiveTelemetryDaemon")
        cls._thread.start()
        logger.info("LiveTelemetryDaemon started successfully.")

    @classmethod
    def stop(cls):
        """Stop the live background daemon thread."""
        cls._running = False
        if cls._thread and cls._thread.is_alive():
            cls._thread.join(timeout=2.0)
        cls._thread = None
        logger.info("LiveTelemetryDaemon stopped.")
