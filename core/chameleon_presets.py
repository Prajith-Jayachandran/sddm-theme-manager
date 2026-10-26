"""
SDDM Theme Manager - "OS Chameleon" 1-Click Distro Hopper Presets (Feature 18)
Generates complete, pixel-perfect SDDM theme templates mimicking iconic operating systems:
macOS Sequoia Aerial, Windows 11 Fluent Mica, Steam Deck OLED Console, and Cyberpunk 2077 HUD.
"""

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class ChameleonPreset:
    id: str
    name: str
    os_family: str
    description: str
    primary_color: str
    accent_color: str
    main_qml_template: str
    theme_conf_content: str
    metadata_content: str


MACOS_QML = """import QtQuick 2.15
import QtQuick.Window 2.15

Rectangle {
    id: root
    width: Screen.width > 0 ? Screen.width : 1920
    height: Screen.height > 0 ? Screen.height : 1080
    color: "#0f172a"

    // macOS Sequoia Top Menu Bar
    Rectangle {
        id: menuBar
        anchors.top: parent.top
        width: parent.width
        height: 28
        color: Qt.rgba(0.08, 0.08, 0.12, 0.6)

        Row {
            anchors.left: parent.left
            anchors.leftMargin: 18
            anchors.verticalCenter: parent.verticalCenter
            spacing: 16

            Text { text: ""; color: "#f8fafc"; font.pixelSize: 15 }
            Text { text: "SDDM Greeter"; color: "#f8fafc"; font.pixelSize: 12; font.bold: true }
        }

        Row {
            anchors.right: parent.right
            anchors.rightMargin: 18
            anchors.verticalCenter: parent.verticalCenter
            spacing: 14

            Text { text: "📶"; font.pixelSize: 12 }
            Text { text: "🔋 100%"; color: "#f8fafc"; font.pixelSize: 12 }
            Text {
                text: Qt.formatDateTime(new Date(), "ddd MMM d  h:mm AP")
                color: "#f8fafc"
                font.pixelSize: 12
            }
        }
    }

    // Centered macOS Avatar & Login Capsule
    Column {
        anchors.centerIn: parent
        spacing: 16

        Rectangle {
            width: 104
            height: 104
            radius: 52
            color: "#1e293b"
            border.color: Qt.rgba(1, 1, 1, 0.3)
            border.width: 2
            anchors.horizontalCenter: parent.horizontalCenter

            Text {
                anchors.centerIn: parent
                text: "👤"
                font.pixelSize: 48
            }
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Administrator"
            color: "#ffffff"
            font.bold: true
            font.pixelSize: 18
        }

        Rectangle {
            width: 220
            height: 36
            radius: 18
            color: Qt.rgba(1, 1, 1, 0.2)
            border.color: Qt.rgba(1, 1, 1, 0.4)
            border.width: 1
            anchors.horizontalCenter: parent.horizontalCenter

            TextInput {
                id: passInput
                anchors.fill: parent
                anchors.margins: 8
                echoMode: TextInput.Password
                color: "#ffffff"
                font.pixelSize: 14
                verticalAlignment: TextInput.AlignVCenter
                horizontalAlignment: TextInput.AlignHCenter
                focus: true
            }

            Text {
                anchors.centerIn: parent
                text: "Enter Password"
                color: Qt.rgba(1, 1, 1, 0.5)
                font.pixelSize: 13
                visible: !passInput.text
            }
        }
    }
}
"""

WINDOWS11_QML = """import QtQuick 2.15
import QtQuick.Window 2.15

Rectangle {
    id: root
    width: Screen.width > 0 ? Screen.width : 1920
    height: Screen.height > 0 ? Screen.height : 1080
    color: "#0b1220"

    // Windows 11 Centered Time & Date (Spotlight Style)
    Column {
        anchors.top: parent.top
        anchors.topMargin: parent.height * 0.15
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: 4

        Text {
            text: Qt.formatDateTime(new Date(), "hh:mm")
            color: "#ffffff"
            font.pixelSize: 76
            font.weight: Font.DemiBold
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Text {
            text: Qt.formatDateTime(new Date(), "dddd, MMMM d")
            color: "#cbd5e1"
            font.pixelSize: 20
            anchors.horizontalCenter: parent.horizontalCenter
        }
    }

    // Windows 11 Acrylic Login Card
    Rectangle {
        width: 320
        height: 240
        radius: 12
        color: Qt.rgba(0.12, 0.16, 0.24, 0.75)
        border.color: Qt.rgba(1, 1, 1, 0.15)
        border.width: 1
        anchors.centerIn: parent
        anchors.verticalCenterOffset: 60

        Column {
            anchors.centerIn: parent
            spacing: 14

            Rectangle {
                width: 72
                height: 72
                radius: 36
                color: "#1e293b"
                border.color: "#38bdf8"
                border.width: 2
                anchors.horizontalCenter: parent.horizontalCenter

                Text {
                    anchors.centerIn: parent
                    text: "👤"
                    font.pixelSize: 34
                }
            }

            Text {
                text: "Windows User"
                color: "#ffffff"
                font.bold: true
                font.pixelSize: 16
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Rectangle {
                width: 240
                height: 38
                radius: 6
                color: "#0f172a"
                border.color: "#38bdf8"
                border.width: 1

                TextInput {
                    anchors.fill: parent
                    anchors.margins: 8
                    echoMode: TextInput.Password
                    color: "#ffffff"
                    font.pixelSize: 14
                    verticalAlignment: TextInput.AlignVCenter
                }
            }
        }
    }
}
"""

STEAM_DECK_QML = """import QtQuick 2.15
import QtQuick.Window 2.15

Rectangle {
    id: root
    width: Screen.width > 0 ? Screen.width : 1920
    height: Screen.height > 0 ? Screen.height : 1080
    color: "#0e141b"

    // Steam Top Header
    Rectangle {
        width: parent.width
        height: 48
        color: "#171d25"

        Row {
            anchors.left: parent.left
            anchors.leftMargin: 24
            anchors.verticalCenter: parent.verticalCenter
            spacing: 12

            Text { text: "🎮 STEAM DECK"; color: "#1a9fff"; font.bold: true; font.pixelSize: 16 }
        }

        Row {
            anchors.right: parent.right
            anchors.rightMargin: 24
            anchors.verticalCenter: parent.verticalCenter
            spacing: 16

            Text { text: "⚡ 98%"; color: "#ffffff"; font.pixelSize: 13 }
            Text { text: Qt.formatDateTime(new Date(), "h:mm AP"); color: "#ffffff"; font.pixelSize: 13 }
        }
    }

    // Console Selection Tile
    Rectangle {
        width: 380
        height: 200
        radius: 8
        color: "#1b2838"
        border.color: "#1a9fff"
        border.width: 3
        anchors.centerIn: parent

        Column {
            anchors.centerIn: parent
            spacing: 14

            Text {
                text: "Steam Gamer"
                color: "#ffffff"
                font.bold: true
                font.pixelSize: 22
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Rectangle {
                width: 260
                height: 42
                radius: 4
                color: "#2a475e"

                Text {
                    anchors.centerIn: parent
                    text: "Press (A) to Log In"
                    color: "#67c1f5"
                    font.bold: true
                    font.pixelSize: 14
                }
            }
        }
    }
}
"""

CYBERPUNK_QML = """import QtQuick 2.15
import QtQuick.Window 2.15

Rectangle {
    id: root
    width: Screen.width > 0 ? Screen.width : 1920
    height: Screen.height > 0 ? Screen.height : 1080
    color: "#05070a"

    // Cyberpunk Neon Glitch Lines
    Rectangle {
        anchors.top: parent.top
        width: parent.width
        height: 4
        color: "#fcee0a"
    }

    // Biometric Telemetry Box
    Rectangle {
        width: 380
        height: 280
        color: Qt.rgba(0.04, 0.08, 0.12, 0.9)
        border.color: "#00f0ff"
        border.width: 2
        anchors.centerIn: parent

        Column {
            anchors.centerIn: parent
            spacing: 16

            Text {
                text: "// NETWATCH SECURITY SUITE //"
                color: "#fcee0a"
                font.bold: true
                font.pixelSize: 13
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Rectangle {
                width: 80
                height: 80
                radius: 40
                color: "transparent"
                border.color: "#ff003c"
                border.width: 2
                anchors.horizontalCenter: parent.horizontalCenter

                Text {
                    anchors.centerIn: parent
                    text: "⚡"
                    font.pixelSize: 36
                }
            }

            Text {
                text: "IDENTITY: EDGERUNNER"
                color: "#00f0ff"
                font.bold: true
                font.pixelSize: 15
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Rectangle {
                width: 280
                height: 38
                color: "#0a131f"
                border.color: "#fcee0a"
                border.width: 1

                TextInput {
                    anchors.fill: parent
                    anchors.margins: 8
                    echoMode: TextInput.Password
                    color: "#fcee0a"
                    font.pixelSize: 14
                    verticalAlignment: TextInput.AlignVCenter
                }
            }
        }
    }
}
"""


class ChameleonPresetsManager:
    """Manages full OS chameleon theme presets and generation."""

    PRESETS: List[ChameleonPreset] = [
        ChameleonPreset(
            id="macos_sequoia",
            name="macOS Sequoia Aerial",
            os_family="macOS",
            description="Dynamic aerial blur with clean top menu bar, Apple logo, and centered avatar",
            primary_color="#0f172a",
            accent_color="#38bdf8",
            main_qml_template=MACOS_QML,
            theme_conf_content="[General]\nfontSize=13\nfontFamily=Inter\n",
            metadata_content="[SddmGreeterTheme]\nName=macOS Sequoia Aerial\nType=sddm-theme\nVersion=1.0\nAuthor=SDDM Chameleon\nMainScript=Main.qml\n",
        ),
        ChameleonPreset(
            id="windows11_fluent",
            name="Windows 11 Fluent Acrylic",
            os_family="Windows",
            description="Mica translucent acrylic card with centered spotlight clock and fluent PIN pad",
            primary_color="#0b1220",
            accent_color="#38bdf8",
            main_qml_template=WINDOWS11_QML,
            theme_conf_content="[General]\nfontSize=14\nfontFamily=Segoe UI\n",
            metadata_content="[SddmGreeterTheme]\nName=Windows 11 Fluent Acrylic\nType=sddm-theme\nVersion=1.0\nAuthor=SDDM Chameleon\nMainScript=Main.qml\n",
        ),
        ChameleonPreset(
            id="steam_deck_oled",
            name="Steam Deck OLED Console",
            os_family="SteamOS",
            description="Big Picture gaming console interface with controller navigation styling",
            primary_color="#0e141b",
            accent_color="#1a9fff",
            main_qml_template=STEAM_DECK_QML,
            theme_conf_content="[General]\nfontSize=14\nfontFamily=Motiva Sans\n",
            metadata_content="[SddmGreeterTheme]\nName=Steam Deck OLED Console\nType=sddm-theme\nVersion=1.0\nAuthor=SDDM Chameleon\nMainScript=Main.qml\n",
        ),
        ChameleonPreset(
            id="cyberpunk_hud",
            name="Cyberpunk 2077 Netwatch HUD",
            os_family="Cyberpunk",
            description="High-contrast neon glitch styling with biometric wireframes and cyber telemetry",
            primary_color="#05070a",
            accent_color="#00f0ff",
            main_qml_template=CYBERPUNK_QML,
            theme_conf_content="[General]\nfontSize=13\nfontFamily=Rajdhani\n",
            metadata_content="[SddmGreeterTheme]\nName=Cyberpunk 2077 Netwatch HUD\nType=sddm-theme\nVersion=1.0\nAuthor=SDDM Chameleon\nMainScript=Main.qml\n",
        ),
    ]

    @classmethod
    def list_presets(cls) -> List[ChameleonPreset]:
        return cls.PRESETS

    @classmethod
    def get_preset_by_id(cls, preset_id: str) -> Optional[ChameleonPreset]:
        for p in cls.PRESETS:
            if p.id == preset_id:
                return p
        return None

    @classmethod
    def export_preset_to_theme(cls, preset_id: str, dest_dir: Path) -> Tuple[bool, str]:
        """Generate a complete standalone SDDM theme package from the preset."""
        preset = cls.get_preset_by_id(preset_id)
        if not preset:
            return False, f"Unknown chameleon preset '{preset_id}'."

        dest_dir = Path(dest_dir).resolve()
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            (dest_dir / "Main.qml").write_text(preset.main_qml_template, encoding="utf-8")
            (dest_dir / "metadata.desktop").write_text(preset.metadata_content, encoding="utf-8")
            (dest_dir / "theme.conf").write_text(preset.theme_conf_content, encoding="utf-8")
            return True, f"Theme '{preset.name}' generated at {dest_dir}."
        except Exception as e:
            return False, f"Failed to generate theme: {e}"
