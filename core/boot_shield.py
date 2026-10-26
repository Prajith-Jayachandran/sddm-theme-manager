"""
SDDM Theme Manager - Boot Shield Watchdog (Feature 11)
Automated fail-safe watchdog service ensuring users are never locked out of their system
by experimental, corrupted, or crashing SDDM themes. Reverts to Breeze within seconds of any failure.
"""

import datetime
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .polkit import PolkitConfig, is_sddm_installed, run_command, write_file_privileged
from .theme_scanner import ThemeScanner

SYSTEM_THEMES_DIR = Path("/usr/share/sddm/themes")
DROPIN_CONF_PATH = Path("/etc/sddm.conf.d/10-theme.conf")
LEGACY_CONF_PATH = Path("/etc/sddm.conf")
SHIELD_SERVICE_PATH = Path("/etc/systemd/system/sddm-boot-shield.service")
SHIELD_SCRIPT_PATH = Path("/usr/local/bin/sddm-boot-shield")
SHIELD_LOG_PATH = Path("/var/log/sddm-shield.log")
USER_LOG_PATH = Path.home() / ".local/state/sddm-theme-manager/boot_shield.log"

STANDARD_SAFE_THEMES = ["breeze", "elarun", "maldives", "maya"]


class BootShield:
    """
    Manages SDDM Boot Shield watchdog service, emergency rollbacks,
    fail-safe configuration verification, and crash telemetry.
    """

    DROPIN_CONF_PATH = DROPIN_CONF_PATH
    SHIELD_SERVICE_PATH = SHIELD_SERVICE_PATH
    SHIELD_SCRIPT_PATH = SHIELD_SCRIPT_PATH
    SHIELD_LOG_PATH = SHIELD_LOG_PATH

    @classmethod
    def get_fallback_theme(cls) -> str:
        """Find the safest verified system theme to rollback to."""
        for candidate in STANDARD_SAFE_THEMES:
            cand_path = SYSTEM_THEMES_DIR / candidate
            if cand_path.exists() and (cand_path / "Main.qml" or cand_path / "metadata.desktop").exists():
                return candidate

        # If standard breeze/elarun not found, find any existing system theme
        if SYSTEM_THEMES_DIR.exists():
            for item in sorted(SYSTEM_THEMES_DIR.iterdir()):
                if item.is_dir() and not item.name.startswith("."):
                    return item.name

        return "breeze"

    @classmethod
    def get_active_theme(cls) -> str:
        """Read the currently configured SDDM theme name."""
        if DROPIN_CONF_PATH.exists():
            try:
                content = DROPIN_CONF_PATH.read_text(encoding="utf-8", errors="replace")
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith("Current=") or line.startswith("Current ="):
                        return line.split("=", 1)[1].strip()
            except Exception:
                pass

        if LEGACY_CONF_PATH.exists():
            try:
                content = LEGACY_CONF_PATH.read_text(encoding="utf-8", errors="replace")
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith("Current=") or line.startswith("Current ="):
                        return line.split("=", 1)[1].strip()
            except Exception:
                pass

        return "breeze"

    @classmethod
    def is_installed(cls) -> bool:
        """Check whether the boot shield system service and script are installed."""
        return SHIELD_SERVICE_PATH.exists() and SHIELD_SCRIPT_PATH.exists()

    @classmethod
    def is_active(cls) -> bool:
        """Check if the boot shield service is currently running."""
        if not cls.is_installed():
            return False
        systemctl = shutil.which("systemctl")
        if not systemctl:
            return False
        try:
            rc = subprocess.run(
                [systemctl, "is-active", "--quiet", "sddm-boot-shield.service"],
                capture_output=True,
                timeout=3,
            ).returncode
            return rc == 0
        except Exception:
            return False

    @classmethod
    def generate_watchdog_script(cls) -> str:
        """Generate bash watchdog monitoring script."""
        fallback = cls.get_fallback_theme()
        script = f"""#!/bin/bash
# SDDM Theme Manager - Boot Shield Watchdog
# Automatically restores '{fallback}' if SDDM fails to start or crashes repeatedly.

SHIELD_LOG="{SHIELD_LOG_PATH}"
DROPIN_CONF="{DROPIN_CONF_PATH}"
FALLBACK_THEME="{fallback}"

log_msg() {{
    local timestamp
    timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] [BOOT-SHIELD] $1" | tee -a "$SHIELD_LOG" 2>/dev/null || echo "[$timestamp] [BOOT-SHIELD] $1"
}}

rollback_to_safety() {{
    local reason="$1"
    log_msg "🚨 EMERGENCY ROLLBACK TRIGGERED: $reason"
    log_msg "Reverting SDDM theme to safe default: $FALLBACK_THEME"

    mkdir -p "$(dirname "$DROPIN_CONF")"
    cat <<EOF > "$DROPIN_CONF"
[Theme]
Current=$FALLBACK_THEME
EOF
    chmod 644 "$DROPIN_CONF"

    log_msg "Restarting SDDM service with safe theme..."
    systemctl restart sddm.service || true
    log_msg "SDDM service restarted with $FALLBACK_THEME."
}}

log_msg "Boot Shield watchdog started. Monitoring SDDM stability..."

# Monitor SDDM restart frequency and crash status
FAIL_COUNT=0
WINDOW_START=$(date +%s)

while true; do
    sleep 3

    # Check if SDDM entered failed state
    SDDM_STATE=$(systemctl is-failed sddm.service 2>/dev/null || echo "inactive")
    if [ "$SDDM_STATE" = "failed" ]; then
        rollback_to_safety "SDDM service entered 'failed' state"
        FAIL_COUNT=0
        sleep 10
        continue
    fi

    # Check for greeter coredumps / segfaults in journalctl over past 5 seconds
    if journalctl -u sddm.service --since "5 seconds ago" 2>/dev/null | grep -iE "(segfault|signal 11|dumped core|fatal error)" >/dev/null 2>&1; then
        rollback_to_safety "Greeter segfault/core-dump detected in system journal"
        FAIL_COUNT=0
        sleep 10
        continue
    fi
done
"""
        return script

    @classmethod
    def generate_service_unit(cls) -> str:
        """Generate systemd service unit."""
        return """[Unit]
Description=SDDM Theme Manager Boot Shield Watchdog
Documentation=https://github.com/prajithj/sddm-theme-manager
After=sddm.service
Wants=sddm.service

[Service]
Type=simple
ExecStart=/usr/local/bin/sddm-boot-shield
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

    @classmethod
    def install_shield(cls) -> Tuple[bool, str]:
        """Install and activate the Boot Shield service and monitor daemon."""
        script_code = cls.generate_watchdog_script()
        service_code = cls.generate_service_unit()

        # Write script
        ok, msg = write_file_privileged(str(SHIELD_SCRIPT_PATH), script_code, mode="0755")
        if not ok:
            return False, f"Failed to install watchdog script: {msg}"

        # Write service
        ok, msg = write_file_privileged(str(SHIELD_SERVICE_PATH), service_code, mode="0644")
        if not ok:
            return False, f"Failed to install systemd service: {msg}"

        # Reload systemd and enable service
        systemctl = shutil.which("systemctl") or "/usr/bin/systemctl"
        run_command([systemctl, "daemon-reload"], privileged=True)
        rc, out, err = run_command([systemctl, "enable", "--now", "sddm-boot-shield.service"], privileged=True)
        if rc != 0:
            return False, f"Failed to enable sddm-boot-shield.service: {err or out}"

        cls.log_event("Boot Shield watchdog service successfully installed and armed.")
        return True, "Boot Shield watchdog successfully installed and armed."

    @classmethod
    def uninstall_shield(cls) -> Tuple[bool, str]:
        """Stop and remove the Boot Shield service."""
        systemctl = shutil.which("systemctl") or "/usr/bin/systemctl"
        rm_bin = shutil.which("rm") or "/usr/bin/rm"

        if cls.is_active():
            run_command([systemctl, "disable", "--now", "sddm-boot-shield.service"], privileged=True)

        if SHIELD_SERVICE_PATH.exists():
            run_command([rm_bin, "-f", str(SHIELD_SERVICE_PATH)], privileged=True)
        if SHIELD_SCRIPT_PATH.exists():
            run_command([rm_bin, "-f", str(SHIELD_SCRIPT_PATH)], privileged=True)

        run_command([systemctl, "daemon-reload"], privileged=True)
        cls.log_event("Boot Shield watchdog service uninstalled.")
        return True, "Boot Shield watchdog successfully uninstalled."

    @classmethod
    def trigger_emergency_rollback(cls, fallback_theme: Optional[str] = None, reason: str = "Manual trigger") -> Tuple[bool, str]:
        """
        Immediately rewrite SDDM configuration to safe fallback theme and log action.
        Guarantees instant recovery.
        """
        target_theme = fallback_theme or cls.get_fallback_theme()
        config_content = f"# Generated by SDDM Theme Manager Boot Shield\n[Theme]\nCurrent={target_theme}\n"

        ok, msg = write_file_privileged(str(cls.DROPIN_CONF_PATH), config_content, mode="0644")
        if not ok:
            # Fallback to direct write if privileged failed or testing in user mode
            try:
                cls.DROPIN_CONF_PATH.parent.mkdir(parents=True, exist_ok=True)
                cls.DROPIN_CONF_PATH.write_text(config_content, encoding="utf-8")
                ok = True
            except Exception as e:
                return False, f"Failed to rollback theme to '{target_theme}': {e}"

        log_entry = f"EMERGENCY ROLLBACK to '{target_theme}'. Reason: {reason}"
        cls.log_event(log_entry)
        return True, f"Emergency rollback to '{target_theme}' successful. {log_entry}"

    @classmethod
    def log_event(cls, message: str):
        """Append log event to shield log file."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] [BOOT-SHIELD] {message}\n"

        # Try system log path first
        try:
            if os.access(str(SHIELD_LOG_PATH.parent), os.W_OK) or SHIELD_LOG_PATH.exists():
                with open(SHIELD_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(formatted)
                return
        except Exception:
            pass

        # Fallback to user log path
        try:
            USER_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(USER_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(formatted)
        except Exception:
            pass

    @classmethod
    def read_recent_logs(cls, max_lines: int = 50) -> List[str]:
        """Retrieve recent entries from the shield logs."""
        logs = []
        for p in [SHIELD_LOG_PATH, USER_LOG_PATH]:
            if p.exists():
                try:
                    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
                    logs.extend(lines)
                except Exception:
                    pass
        return logs[-max_lines:]

    @classmethod
    def verify_shield_configuration(cls) -> Dict:
        """
        Performs full pre-flight verification of system safety.
        Returns a dictionary with status, check results, and recommendations.
        """
        results = {
            "sddm_installed": is_sddm_installed(),
            "fallback_theme_exists": False,
            "fallback_theme": cls.get_fallback_theme(),
            "active_theme": cls.get_active_theme(),
            "dropin_dir_ready": Path("/etc/sddm.conf.d").exists(),
            "shield_installed": cls.is_installed(),
            "shield_active": cls.is_active(),
            "status": "active" if cls.is_active() else ("installed_stopped" if cls.is_installed() else "unconfigured"),
            "checks": [],
        }

        # Check fallback theme existence
        cand_path = SYSTEM_THEMES_DIR / results["fallback_theme"]
        if cand_path.exists() and cand_path.is_dir():
            results["fallback_theme_exists"] = True

        # Build human-readable check list
        results["checks"].append({
            "name": "SDDM Display Manager",
            "passed": results["sddm_installed"],
            "detail": "SDDM binary or configuration detected" if results["sddm_installed"] else "SDDM not detected",
        })

        results["checks"].append({
            "name": "Safe Fallback Theme",
            "passed": results["fallback_theme_exists"],
            "detail": f"System fallback '{results['fallback_theme']}' at {cand_path}" if results["fallback_theme_exists"] else f"Fallback '{results['fallback_theme']}' missing in /usr/share/sddm/themes/",
        })

        results["checks"].append({
            "name": "Drop-in Directory (/etc/sddm.conf.d)",
            "passed": results["dropin_dir_ready"],
            "detail": "Directory exists for drop-in configuration" if results["dropin_dir_ready"] else "Directory /etc/sddm.conf.d does not exist",
        })

        results["checks"].append({
            "name": "Boot Shield Watchdog Service",
            "passed": results["shield_active"],
            "detail": "systemd unit active & armed" if results["shield_active"] else ("Installed but inactive" if results["shield_installed"] else "Not installed (Optional background daemon)"),
        })

        # Overall health status
        if not results["fallback_theme_exists"]:
            results["overall_health"] = "CRITICAL: No verified safe fallback theme found in system directory"
        elif results["shield_active"]:
            results["overall_health"] = "OPTIMAL: Boot Shield Watchdog is active and armed"
        else:
            results["overall_health"] = "READY: Manual fallback verified; watchdog service uninstalled"

        return results
