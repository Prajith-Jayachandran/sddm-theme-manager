"""
SDDM Theme Manager - Theme Next-Gen Feature Enhancer
Analyzes, injects, and configures Next-Gen features (Startup Audio, GLSL Shaders,
Weather/Cosmos, MPRIS Capsule, System HUD, Sticky Notes, Passkey, FIDO2, Mini-Games)
into existing installed SDDM themes with automated fail-safe backup and clean reversal.
"""

import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .audio_chime import AudioChimeManager
from .fido2_detector import FIDO2Detector
from .greeter_games import GreeterGamesManager
from .mpris_bridge import MPRISBridge
from .passkey_server import PasskeyAuthServer
from .polkit import run_command, write_file_privileged
from .shader_engine import ShaderEngine
from .solar_timelapse import SolarTimelapseManager
from .sticky_notes import StickyNotesManager
from .system_hud import SystemHUDTelemetry
from .weather_service import WeatherService


class ThemeEnhancer:
    """Manages feature injection, inspection, and rollback for existing SDDM themes."""

    BACKUP_SUFFIX = ".pre_enhance_bak"

    @classmethod
    def get_main_qml_path(cls, theme_path: Path) -> Optional[Path]:
        """Find the main QML script for a theme."""
        p = Path(theme_path).resolve()
        for cand in ["Main.qml", "main.qml"]:
            target = p / cand
            if target.exists():
                return target
        return None

    @classmethod
    def inspect_theme_features(cls, theme_path: Path) -> Dict[str, bool]:
        """
        Inspect which Next-Gen features are active or injected into the specified theme.
        """
        theme_dir = Path(theme_path).resolve()
        main_qml = cls.get_main_qml_path(theme_dir)
        content = ""
        if main_qml and main_qml.exists():
            try:
                content = main_qml.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass

        audio_conf = AudioChimeManager.load_config()
        chime_active = audio_conf.get("enabled", False)

        return {
            "boot_chime": chime_active,
            "shader_bg": "ShaderBackground" in content or (theme_dir / "ShaderBackground.qml").exists(),
            "weather_cosmos": "WeatherCanvas" in content or (theme_dir / "WeatherCanvas.qml").exists(),
            "mpris_capsule": "MediaCapsule" in content or (theme_dir / "MediaCapsule.qml").exists(),
            "system_hud": "SystemHUD" in content or (theme_dir / "SystemHUD.qml").exists(),
            "sticky_notes": "StickyNotesWidget" in content or (theme_dir / "StickyNotesWidget.qml").exists(),
            "passkey_qr": "PasskeyWidget" in content or (theme_dir / "PasskeyWidget.qml").exists(),
            "fido2_visualizer": "Fido2Visualizer" in content or (theme_dir / "Fido2Visualizer.qml").exists(),
            "mini_games": "GameFlappytux" in content or (theme_dir / "GameFlappytux.qml").exists(),
        }

    @classmethod
    def equip_all_nextgen_features(
        cls,
        theme_path: Path,
        chime_preset: str = "mac_retro",
        shader_preset: str = "matrix_rain",
    ) -> Tuple[bool, str]:
        """
        1-Click batch upgrade equipping all Next-Gen features into any existing SDDM theme.
        Creates an automated backup of Main.qml before injection.
        """
        theme_dir = Path(theme_path).resolve()
        main_qml = cls.get_main_qml_path(theme_dir)
        if not main_qml or not main_qml.exists():
            return False, f"Could not find Main.qml in {theme_dir}"

        # 1. Enable SDDM Startup Boot Chime
        chime_ok, chime_msg = AudioChimeManager.install_sddm_chime_hook(chime_preset)

        # 2. Backup Main.qml if not already backed up
        backup_file = theme_dir / (main_qml.name + cls.BACKUP_SUFFIX)
        if not backup_file.exists():
            try:
                if os.access(theme_dir, os.W_OK):
                    shutil.copy2(main_qml, backup_file)
                else:
                    cp_bin = shutil.which("cp") or "/usr/bin/cp"
                    run_command([cp_bin, str(main_qml), str(backup_file)], privileged=True)
            except Exception as e:
                return False, f"Failed to create backup of {main_qml.name}: {e}"

        # 3. Generate and write component QML files into theme directory
        components = {
            "ShaderBackground.qml": ShaderEngine.generate_qml_component(
                ShaderEngine.get_preset_by_id(shader_preset) or ShaderEngine.PRESETS[0]
            ),
            "WeatherCanvas.qml": WeatherService.generate_weather_qml(WeatherService.fetch_weather(timeout=1)),
            "MediaCapsule.qml": MPRISBridge.generate_capsule_qml(),
            "SystemHUD.qml": SystemHUDTelemetry.generate_hud_qml(),
            "StickyNotesWidget.qml": StickyNotesManager.generate_notes_qml(),
            "PasskeyWidget.qml": PasskeyAuthServer.generate_passkey_qml(PasskeyAuthServer.create_session("User")),
            "Fido2Visualizer.qml": FIDO2Detector.generate_visualizer_qml(),
            "GameFlappytux.qml": GreeterGamesManager.GAMES[0].qml_source,
        }

        for filename, code in components.items():
            dest = theme_dir / filename
            if os.access(theme_dir, os.W_OK):
                dest.write_text(code, encoding="utf-8")
            else:
                ok, msg = write_file_privileged(dest, code, mode="0644")
                if not ok:
                    return False, f"Failed to write component {filename}: {msg}"

        # 4. Inject component references into Main.qml
        try:
            content = main_qml.read_text(encoding="utf-8", errors="replace")

            # Check if root item opening exists: Rectangle { or Item { or FocusScope {
            match = re.search(r"((?:Rectangle|Item|FocusScope)\s*\{)", content)
            if not match:
                return False, "Could not find root Item/Rectangle in Main.qml to attach features."

            injection_blocks = [
                "\n    // --- SDDM THEME MANAGER NEXT-GEN MASTER SUITE INJECTIONS ---",
                "    ShaderBackground { id: nextgenShaderBg; anchors.fill: parent; z: -1; opacity: 0.85 }",
                "    WeatherCanvas { id: nextgenWeather; anchors.fill: parent; z: 5; opacity: 0.9 }",
                "    Row {",
                "        id: nextgenTopBar",
                "        anchors.top: parent.top",
                "        anchors.horizontalCenter: parent.horizontalCenter",
                "        anchors.topMargin: 12",
                "        spacing: 12",
                "        z: 30",
                "        MediaCapsule { id: nextgenMedia; anchors.verticalCenter: parent.verticalCenter }",
                "        Fido2Visualizer { id: nextgenFido; anchors.verticalCenter: parent.verticalCenter }",
                "        SystemHUD { id: nextgenHud; anchors.verticalCenter: parent.verticalCenter }",
                "    }",
                "    Row {",
                "        id: nextgenActionDock",
                "        anchors.top: parent.top",
                "        anchors.right: parent.right",
                "        anchors.margins: 12",
                "        spacing: 8",
                "        z: 40",
                "        PasskeyWidget { id: nextgenPasskey }",
                "        StickyNotesWidget { id: nextgenNotes }",
                "        Rectangle {",
                "            id: nextgenGamePill",
                "            width: 78; height: 32; radius: 16",
                "            color: nextgenGameMouse.containsMouse ? '#1e293b' : Qt.rgba(0.07, 0.09, 0.15, 0.85)",
                "            border.color: nextgenGameMouse.containsMouse ? '#ec4899' : Qt.rgba(0.3, 0.45, 0.7, 0.4)",
                "            border.width: 1",
                "            Row {",
                "                anchors.centerIn: parent",
                "                spacing: 4",
                "                Text { text: '🎮'; font.pixelSize: 12 }",
                "                Text { text: 'Play'; color: '#cbd5e1'; font.bold: true; font.pixelSize: 11 }",
                "            }",
                "            MouseArea {",
                "                id: nextgenGameMouse",
                "                anchors.fill: parent",
                "                hoverEnabled: true",
                "                cursorShape: Qt.PointingHandCursor",
                "                onClicked: nextgenGame.visible = !nextgenGame.visible",
                "            }",
                "        }",
                "    }",
                "    GameFlappytux { id: nextgenGame; visible: false; z: 99; anchors.centerIn: parent }",
                "    Shortcut { sequence: 'Ctrl+Alt+G'; onActivated: nextgenGame.visible = !nextgenGame.visible }",
                "    Shortcut { sequence: 'Ctrl+Alt+F'; onActivated: nextgenGame.visible = !nextgenGame.visible }",
                "    // --- END NEXT-GEN SUITE INJECTIONS ---\n",
            ]

            # Only inject if not already present
            if "nextgenShaderBg" not in content:
                injected_code = "\n".join(injection_blocks)
                new_content = content[: match.end()] + "\n" + injected_code + content[match.end() :]

                if os.access(theme_dir, os.W_OK):
                    main_qml.write_text(new_content, encoding="utf-8")
                else:
                    ok, msg = write_file_privileged(main_qml, new_content, mode="0644")
                    if not ok:
                        return False, f"Failed to update Main.qml: {msg}"

            return True, f"Theme '{theme_dir.name}' successfully upgraded with Next-Gen Master Suite features."
        except Exception as e:
            return False, f"Failed to modify Main.qml: {e}"

    @classmethod
    def revert_theme_features(cls, theme_path: Path) -> Tuple[bool, str]:
        """
        Reverts an upgraded theme back to its clean original state from backup.
        """
        theme_dir = Path(theme_path).resolve()
        main_qml = cls.get_main_qml_path(theme_dir)
        if not main_qml:
            return False, "Main.qml not found in theme directory."

        backup_file = theme_dir / (main_qml.name + cls.BACKUP_SUFFIX)
        if not backup_file.exists():
            return False, f"No backup file found ({backup_file.name}) to restore from."

        try:
            if os.access(theme_dir, os.W_OK):
                shutil.copy2(backup_file, main_qml)
                backup_file.unlink()
            else:
                cp_bin = shutil.which("cp") or "/usr/bin/cp"
                rm_bin = shutil.which("rm") or "/usr/bin/rm"
                run_command([cp_bin, str(backup_file), str(main_qml)], privileged=True)
                run_command([rm_bin, "-f", str(backup_file)], privileged=True)

            # Clean up injected component files
            components = [
                "ShaderBackground.qml",
                "WeatherCanvas.qml",
                "MediaCapsule.qml",
                "SystemHUD.qml",
                "StickyNotesWidget.qml",
                "PasskeyWidget.qml",
                "Fido2Visualizer.qml",
                "GameFlappytux.qml",
                "GameCyberpong.qml",
            ]
            for c in components:
                cf = theme_dir / c
                if cf.exists():
                    if os.access(theme_dir, os.W_OK):
                        cf.unlink()
                    else:
                        run_command([shutil.which("rm") or "/usr/bin/rm", "-f", str(cf)], privileged=True)

            return True, f"Theme '{theme_dir.name}' successfully restored to clean original state."
        except Exception as e:
            return False, f"Failed to revert theme: {e}"
