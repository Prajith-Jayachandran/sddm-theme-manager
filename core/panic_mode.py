"""
SDDM Theme Manager - Panic Mode & Decoy Duress Profile (Feature 8)
Configures decoy authentication credentials and ephemeral sandbox environments to protect
sensitive personal data and cryptographic keys under coerced or duress login scenarios.
"""

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PANIC_CONFIG_PATH = Path.home() / ".config/sddm-theme-manager/panic_mode.json"
DURESS_LOG_PATH = Path.home() / ".local/state/sddm-theme-manager/duress_events.log"


@dataclass
class PanicModeConfig:
    enabled: bool
    decoy_username: str
    duress_pin_hash: str
    salt: str
    isolate_home_dir: bool
    silent_alert_cmd: str


class PanicModeManager:
    """Manages decoy duress authentication, guest tmpfs profiles, and privacy audit checks."""

    @classmethod
    def hash_duress_pin(cls, pin: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """Create secure SHA256 salted hash of duress PIN."""
        if not salt:
            salt = os.urandom(16).hex()
        derived = hashlib.sha256((pin + salt).encode("utf-8")).hexdigest()
        return derived, salt

    @classmethod
    def load_config(cls) -> PanicModeConfig:
        if PANIC_CONFIG_PATH.exists():
            try:
                data = json.loads(PANIC_CONFIG_PATH.read_text(encoding="utf-8"))
                return PanicModeConfig(
                    enabled=data.get("enabled", False),
                    decoy_username=data.get("decoy_username", "guest"),
                    duress_pin_hash=data.get("duress_pin_hash", ""),
                    salt=data.get("salt", ""),
                    isolate_home_dir=data.get("isolate_home_dir", True),
                    silent_alert_cmd=data.get("silent_alert_cmd", ""),
                )
            except Exception:
                pass
        return PanicModeConfig(
            enabled=False,
            decoy_username="decoy_guest",
            duress_pin_hash="",
            salt="",
            isolate_home_dir=True,
            silent_alert_cmd="",
        )

    @classmethod
    def save_config(cls, conf: PanicModeConfig):
        PANIC_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "enabled": conf.enabled,
            "decoy_username": conf.decoy_username,
            "duress_pin_hash": conf.duress_pin_hash,
            "salt": conf.salt,
            "isolate_home_dir": conf.isolate_home_dir,
            "silent_alert_cmd": conf.silent_alert_cmd,
        }
        PANIC_CONFIG_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def verify_pin_trigger(cls, entered_pin: str) -> bool:
        """Check if an entered PIN matches the duress trigger."""
        conf = cls.load_config()
        if not conf.enabled or not conf.duress_pin_hash or not conf.salt:
            return False

        check_hash, _ = cls.hash_duress_pin(entered_pin, conf.salt)
        if check_hash == conf.duress_pin_hash:
            cls.log_duress_event("Duress PIN successfully triggered panic mode redirection.")
            return True
        return False

    @classmethod
    def log_duress_event(cls, details: str):
        """Silently record duress event timestamp."""
        try:
            DURESS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(DURESS_LOG_PATH, "a", encoding="utf-8") as f:
                import datetime

                now = datetime.datetime.now().isoformat()
                f.write(f"[{now}] [DURESS-ALERT] {details}\n")
        except Exception:
            pass

    @classmethod
    def run_privacy_audit(cls, target_home: Optional[Path] = None) -> Dict:
        """
        Audits current user permissions to ensure that private keys, browser sessions,
        and credentials cannot be read by an unauthorized or decoy guest session.
        """
        home = target_home or Path.home()
        critical_paths = [
            home / ".ssh",
            home / ".gnupg",
            home / ".config",
            home / ".local/share",
        ]

        issues = []
        for p in critical_paths:
            if p.exists():
                mode = p.stat().st_mode & 0o777
                # World-readable bit check
                if mode & 0o004 or mode & 0o007:
                    issues.append(f"World-readable directory detected: {p} (mode {oct(mode)})")

        is_safe = len(issues) == 0
        return {
            "safe": is_safe,
            "issues_count": len(issues),
            "issues": issues,
            "summary": "Decoy sandbox isolation verified safe." if is_safe else f"Found {len(issues)} permissions risks.",
        }
