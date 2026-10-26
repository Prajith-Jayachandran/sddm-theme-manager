#!/usr/bin/env python3
"""
SDDM Theme Manager - Standalone, DE-Agnostic GUI Theme Manager for SDDM.
Works identically on KDE Plasma, GNOME, Hyprland, and other window managers.
"""

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from core.polkit import PolkitConfig
from ui.main_window import MainWindow

__version__ = "1.0.0"


def parse_args():
    parser = argparse.ArgumentParser(
        description="SDDM Theme Manager - Standalone DE-Agnostic SDDM Theme Manager",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--apply-scheduled",
        action="store_true",
        help="Headless execution: check Day/Night schedule and apply the scheduled theme",
    )
    parser.add_argument(
        "--verify-shield",
        action="store_true",
        help="Validate Boot Shield watchdog safety configuration and emergency fallback readiness",
    )
    parser.add_argument(
        "--no-polkit",
        action="store_true",
        help="Development fallback: bypass pkexec and call commands with sudo instead (prints warning)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print all subprocess commands, arguments, stdout, stderr, and debug logs",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"SDDM Theme Manager v{__version__}",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    PolkitConfig.set_options(no_polkit=args.no_polkit, debug=args.debug)

    if args.apply_scheduled:
        from core.scheduler import DayNightScheduler
        ok, msg = DayNightScheduler.apply_scheduled()
        print(f"[{'OK' if ok else 'ERROR'}] {msg}")
        sys.exit(0 if ok else 1)

    if args.verify_shield:
        from core.boot_shield import BootShield
        report = BootShield.verify_shield_configuration()
        print("=" * 60)
        print("  🛡️ SDDM BOOT SHIELD — SYSTEM SAFETY VERIFICATION")
        print("=" * 60)
        for check in report["checks"]:
            mark = "✅ PASS" if check["passed"] else "⚠️ WARN"
            print(f"  {mark}: {check['name']} — {check['detail']}")
        print("-" * 60)
        print(f"  Overall Health : {report['overall_health']}")
        print(f"  Fallback Theme : {report['fallback_theme']}")
        print(f"  Active Theme   : {report['active_theme']}")
        print("=" * 60)
        sys.exit(0)

    # Set application metadata
    app = QApplication(sys.argv)
    app.setApplicationName("SDDM Theme Manager")
    app.setApplicationDisplayName("SDDM Theme Manager")
    app.setOrganizationName("SDDMThemeManager")
    app.setDesktopFileName("sddm-theme-manager")

    # Load Application Icon if available
    base_dir = Path(__file__).parent.resolve()
    icon_paths = [
        base_dir / "resources" / "icons" / "sddm-theme-manager.svg",
        base_dir / "resources" / "icons" / "sddm-theme-manager.png",
        Path("/usr/share/icons/hicolor/scalable/apps/sddm-theme-manager.svg"),
        Path.home() / ".local/share/icons/hicolor/scalable/apps/sddm-theme-manager.svg",
    ]
    for ip in icon_paths:
        if ip.exists():
            app.setWindowIcon(QIcon(str(ip)))
            break

    # Load Stylesheet
    qss_path = base_dir / "ui" / "styles.qss"
    if qss_path.exists():
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
        except Exception as e:
            if args.debug:
                print(f"[DEBUG] Failed to load stylesheet: {e}", file=sys.stderr)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
