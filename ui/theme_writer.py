"""
SDDM Theme Manager - Polkit-Aware Theme Writer
Handles writes to system and user theme directories using D-Bus helper / polkit.
Provides complete theme scaffolding with Qt 6 greeter templates, asset-free minimal mode,
custom wallpaper import, and boilerplate starter packages.
"""

import json
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Tuple

from core.polkit import copy_file_privileged, restart_sddm_service, write_file_privileged

logger = logging.getLogger("sddm_theme_manager.theme_writer")

DBUS_BUS_NAME = "com.sddmthememanager.Helper"
DBUS_OBJECT_PATH = "/com/sddmthememanager/Helper"
DBUS_INTERFACE = "com.sddmthememanager.Helper"

# Verified, fully-featured Qt 6 SDDM Greeter QML template
# Features procedural gradient fallbacks when no background image is set,
# allowing asset-free minimal theme generation with zero missing-image errors.
STARTER_MAIN_QML = """import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import Qt5Compat.GraphicalEffects
import SddmComponents 2.0

Rectangle {
    id: root
    width: Screen.width
    height: Screen.height
    color: "#1a1b26"

    readonly property real s: Math.max(0.75, Math.min(1.5, Screen.height / 1080))
    property int sessionIndex: (sessionModel && sessionModel.lastIndex >= 0) ? sessionModel.lastIndex : 0
    property int userIndex: (userModel && userModel.lastIndex >= 0) ? userModel.lastIndex : 0

    readonly property color colBg: "#1a1b26"
    readonly property color colCard: "#d01f2335"
    readonly property color colBorder: "#3b4261"
    readonly property color colText: (config && config.color) ? config.color : "#c0caf5"
    readonly property color colAccent: (config && config.accentColor) ? config.accentColor : "#7aa2f7"
    readonly property color colSub: "#9aa5ce"

    // Helper models
    ListView {
        id: sessionHelper
        model: sessionModel
        currentIndex: root.sessionIndex
        visible: false
        width: 0; height: 0
        delegate: Item { property string sName: model.name || "" }
    }

    ListView {
        id: userHelper
        model: userModel
        currentIndex: root.userIndex
        visible: false
        width: 0; height: 0
        delegate: Item {
            property string uName: model.realName || model.name || ""
            property string uLogin: model.name || ""
            property string uIcon: model.icon || ""
        }
    }

    // Background wallpaper layer with procedural gradient fallback
    Item {
        id: bgLayer
        anchors.fill: parent

        // Base procedural dark gradient (always active when no image or image loading)
        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#16161e" }
                GradientStop { position: 0.5; color: "#1f2335" }
                GradientStop { position: 1.0; color: "#24283b" }
            }
        }

        // Ambient accent glow when running in procedural / asset-free mode
        Rectangle {
            anchors.fill: parent
            visible: !(bgImage.status === Image.Ready) && !(config && config.type === "color")
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "#181a1b26" }
                GradientStop { position: 0.5; color: "#303d59a1" }
                GradientStop { position: 1.0; color: "#181a1b26" }
            }
        }

        // Wallpaper Image (only rendered if config.background is set and file loads cleanly)
        Image {
            id: bgImage
            anchors.fill: parent
            source: (config && config.background) ? config.background : ""
            fillMode: Image.PreserveAspectCrop
            asynchronous: true
            visible: (source != "") && (status === Image.Ready) && !(config && config.type === "color")
        }

        // Solid color background if explicitly specified
        Rectangle {
            anchors.fill: parent
            color: (config && config.background && config.background.indexOf("#") === 0) ? config.background : root.colBg
            visible: (config && config.type === "color")
        }

        // Vignette gradient overlay for high contrast
        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#aa16161e" }
                GradientStop { position: 0.5; color: "#441a1b26" }
                GradientStop { position: 1.0; color: "#cc16161e" }
            }
        }
    }

    // Top Header: Date/Time (Left) and Session/Power (Right)
    Item {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 80 * s
        anchors.margins: 24 * s

        // Clock & Date (Top-Left)
        Column {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            spacing: 4 * s
            visible: !(config && config.showClock === "false")

            Text {
                id: clockText
                text: Qt.formatTime(new Date(), (config && config.clockFormat === "12h") ? "hh:mm ap" : "HH:mm")
                color: "#ffffff"
                font.pixelSize: 42 * s
                font.bold: true
                font.family: (config && config.font) ? config.font : "sans-serif"

                Timer {
                    interval: 1000
                    running: true
                    repeat: true
                    onTriggered: clockText.text = Qt.formatTime(new Date(), (config && config.clockFormat === "12h") ? "hh:mm ap" : "HH:mm")
                }
            }

            Text {
                id: dateText
                text: Qt.formatDate(new Date(), "dddd, MMMM d, yyyy")
                color: root.colSub
                font.pixelSize: 14 * s
                font.family: (config && config.font) ? config.font : "sans-serif"

                Timer {
                    interval: 60000
                    running: true
                    repeat: true
                    onTriggered: dateText.text = Qt.formatDate(new Date(), "dddd, MMMM d, yyyy")
                }
            }
        }

        // Session & Power actions (Top-Right)
        Row {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            spacing: 12 * s

            // Session selector button
            Rectangle {
                width: sessionText.implicitWidth + 28 * s
                height: 36 * s
                radius: 8 * s
                color: sessionMouse.containsMouse ? "#2f354f" : "#1f2335"
                border.color: sessionMouse.containsMouse ? root.colAccent : root.colBorder
                border.width: 1

                Text {
                    id: sessionText
                    anchors.centerIn: parent
                    text: "🖥️ " + ((sessionHelper.currentItem && sessionHelper.currentItem.sName) ? sessionHelper.currentItem.sName : "Session")
                    color: root.colText
                    font.pixelSize: 12 * s
                    font.bold: true
                }

                MouseArea {
                    id: sessionMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (sessionModel && sessionModel.rowCount() > 0) {
                            root.sessionIndex = (root.sessionIndex + 1) % sessionModel.rowCount();
                        }
                    }
                }
            }

            // Power button: Reboot
            Rectangle {
                width: 36 * s
                height: 36 * s
                radius: 8 * s
                color: restartMouse.containsMouse ? "#2f354f" : "#1f2335"
                border.color: restartMouse.containsMouse ? root.colAccent : root.colBorder
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: "🔄"
                    font.pixelSize: 14 * s
                }

                MouseArea {
                    id: restartMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: sddm.reboot()
                }
            }

            // Power button: Shut Down
            Rectangle {
                width: 36 * s
                height: 36 * s
                radius: 8 * s
                color: powerMouse.containsMouse ? "#db4b4b" : "#1f2335"
                border.color: powerMouse.containsMouse ? "#f7768e" : root.colBorder
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: "⏻"
                    color: powerMouse.containsMouse ? "#ffffff" : root.colText
                    font.pixelSize: 14 * s
                    font.bold: true
                }

                MouseArea {
                    id: powerMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: sddm.powerOff()
                }
            }
        }
    }

    // Centered Login Card
    Rectangle {
        id: loginCard
        width: 360 * s
        height: 380 * s
        anchors.centerIn: parent
        radius: 16 * s
        color: root.colCard
        border.color: root.colBorder
        border.width: 1

        Column {
            anchors.fill: parent
            anchors.margins: 28 * s
            spacing: 16 * s

            // Circular User Avatar
            Item {
                width: 80 * s
                height: 80 * s
                anchors.horizontalCenter: parent.horizontalCenter

                Rectangle {
                    id: avatarBg
                    anchors.fill: parent
                    radius: width / 2
                    color: "#24283b"
                    border.color: root.colAccent
                    border.width: 2 * s

                    Text {
                        anchors.centerIn: parent
                        text: "👤"
                        font.pixelSize: 36 * s
                        visible: !(userIcon.status === Image.Ready)
                    }

                    Image {
                        id: userIcon
                        anchors.fill: parent
                        source: (userHelper.currentItem && userHelper.currentItem.uIcon) ? userHelper.currentItem.uIcon : ""
                        fillMode: Image.PreserveAspectCrop
                        layer.enabled: true
                        layer.effect: OpacityMask {
                            maskSource: Rectangle {
                                width: avatarBg.width
                                height: avatarBg.height
                                radius: width / 2
                            }
                        }
                    }
                }
            }

            // Username display
            Text {
                id: userNameText
                anchors.horizontalCenter: parent.horizontalCenter
                text: (userHelper.currentItem && userHelper.currentItem.uName) ? userHelper.currentItem.uName : (userModel.lastUser ? userModel.lastUser : "User")
                color: "#ffffff"
                font.pixelSize: 18 * s
                font.bold: true

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (userModel && userModel.rowCount() > 0) {
                            root.userIndex = (root.userIndex + 1) % userModel.rowCount();
                        }
                    }
                }
            }

            // Password Input Box
            Rectangle {
                width: parent.width
                height: 44 * s
                radius: 8 * s
                color: "#16161e"
                border.color: passwordInput.activeFocus ? root.colAccent : root.colBorder
                border.width: passwordInput.activeFocus ? 2 : 1

                TextInput {
                    id: passwordInput
                    anchors.fill: parent
                    anchors.leftMargin: 14 * s
                    anchors.rightMargin: 14 * s
                    verticalAlignment: TextInput.AlignVCenter
                    echoMode: TextInput.Password
                    passwordCharacter: "•"
                    color: "#ffffff"
                    selectionColor: root.colAccent
                    selectedTextColor: "#1a1b26"
                    font.pixelSize: 14 * s
                    clip: true
                    focus: true

                    Keys.onReturnPressed: doLogin()
                    Keys.onEnterPressed: doLogin()

                    Text {
                        anchors.fill: parent
                        verticalAlignment: Text.AlignVCenter
                        text: "Password…"
                        color: "#565f89"
                        font.pixelSize: 14 * s
                        visible: !passwordInput.text && !passwordInput.activeFocus
                    }
                }
            }

            // Error feedback
            Text {
                id: errorText
                anchors.horizontalCenter: parent.horizontalCenter
                text: ""
                color: "#f7768e"
                font.pixelSize: 12 * s
                font.bold: true
                visible: text.length > 0
            }

            // Log In Button
            Rectangle {
                id: loginButton
                width: parent.width
                height: 44 * s
                radius: 8 * s
                color: loginMouse.pressed ? "#2e4886" : (loginMouse.containsMouse ? "#5a8af0" : "#3d59a1")
                border.color: root.colAccent
                border.width: 1

                Text {
                    anchors.centerIn: parent
                    text: "Log In"
                    font.bold: true
                    font.pixelSize: 14 * s
                    color: "#ffffff"
                }

                MouseArea {
                    id: loginMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: doLogin()
                }
            }
        }
    }

    // Auto-focus timer for password input
    Timer {
        interval: 200
        running: true
        onTriggered: passwordInput.forceActiveFocus()
    }

    // Authentication handlers
    Connections {
        target: sddm
        function onLoginFailed() {
            errorText.text = "Incorrect password. Please try again.";
            passwordInput.text = "";
            passwordInput.forceActiveFocus();
        }
        function onLoginSucceeded() {
            errorText.text = "";
        }
    }

    function doLogin() {
        var username = (userHelper.currentItem && userHelper.currentItem.uLogin)
            ? userHelper.currentItem.uLogin
            : (userModel.lastUser ? userModel.lastUser : "");
        errorText.text = "";
        sddm.login(username, passwordInput.text, root.sessionIndex);
    }
}
"""


def generate_starter_wallpaper(theme_name: str, width: int = 1920, height: int = 1080):
    """
    Generates an aesthetic modern dark gradient wallpaper image using PySide6 QtGui.
    Returns a QImage object.
    """
    import sys
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QLinearGradient, QPainter, QRadialGradient

    _ = QGuiApplication.instance() or QGuiApplication(sys.argv if hasattr(sys, "argv") else [])

    img = QImage(width, height, QImage.Format.Format_RGB32)
    img.fill(QColor("#1a1b26"))

    painter = QPainter(img)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Base diagonal gradient
        gradient = QLinearGradient(0, 0, width, height)
        gradient.setColorAt(0.0, QColor("#16161e"))
        gradient.setColorAt(0.5, QColor("#1f2335"))
        gradient.setColorAt(1.0, QColor("#24283b"))
        painter.fillRect(0, 0, width, height, gradient)

        # Ambient glow in center-top
        radial = QRadialGradient(QPointF(width * 0.5, height * 0.45), width * 0.45)
        radial.setColorAt(0.0, QColor(122, 162, 247, 50))  # #7aa2f7 glow
        radial.setColorAt(0.7, QColor(187, 154, 247, 25))  # #bb9af7
        radial.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(0, 0, width, height, radial)

        # Subtle decorative grid pattern
        pen = painter.pen()
        pen.setColor(QColor(255, 255, 255, 14))
        pen.setWidth(1)
        painter.setPen(pen)
        for y in range(0, height, 48):
            painter.drawLine(0, y, width, y)
        for x in range(0, width, 48):
            painter.drawLine(x, 0, x, height)

        # Watermark/Theme indicator in lower right corner
        pen.setColor(QColor("#565f89"))
        painter.setPen(pen)
        font = QFont("Sans", 11)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        painter.setFont(font)
        painter.drawText(width - 340, height - 28, f"SDDM THEME  •  {theme_name.upper()}")

    finally:
        painter.end()

    return img


class ThemeWriter:
    """Polkit-aware file writer and theme scaffold manager."""

    @classmethod
    def is_privileged_path(cls, path: str | Path) -> bool:
        """Determines if writing to the specified path requires root privileges."""
        p = Path(path).resolve()
        if str(p).startswith("/usr") or str(p).startswith("/etc"):
            return True
        # Find closest existing parent directory to check write permissions
        curr = p
        while not curr.exists() and curr != curr.parent:
            curr = curr.parent
        return not os.access(curr, os.W_OK)

    @classmethod
    def write_file(cls, path: str | Path, content: str) -> Tuple[bool, str]:
        """
        Writes text content to a destination file.
        Uses direct filesystem write for user paths (~/.local/share/...) and
        elevated polkit D-Bus / pkexec for system paths (/usr/share/...).
        """
        target = Path(path).resolve()

        if not cls.is_privileged_path(target):
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                return True, "File written successfully."
            except Exception as e:
                return False, f"Failed to write user file: {e}"

        # Privileged path: Try D-Bus helper first if available
        try:
            import dbus

            bus = dbus.SystemBus()
            proxy = bus.get_object(DBUS_BUS_NAME, DBUS_OBJECT_PATH)
            helper = dbus.Interface(proxy, DBUS_INTERFACE)
            ok, msg = helper.WriteFile(str(target), content)
            if ok:
                return True, str(msg)
        except Exception:
            # Fall back to pkexec / sudo wrapper
            pass

        return write_file_privileged(target, content)

    @classmethod
    def write_binary_file(cls, path: str | Path, source_file: str | Path) -> Tuple[bool, str]:
        """
        Writes a binary file to the destination path.
        Direct copy for user paths, copy_file_privileged for privileged paths.
        """
        target = Path(path).resolve()
        src = Path(source_file).resolve()

        if not cls.is_privileged_path(target):
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, target)
                return True, "File written successfully."
            except Exception as e:
                return False, f"Failed to copy file: {e}"

        return copy_file_privileged(src, target)

    @classmethod
    def restart_sddm(cls) -> Tuple[bool, str]:
        """Restarts SDDM display manager via D-Bus helper or pkexec systemctl."""
        try:
            import dbus

            bus = dbus.SystemBus()
            proxy = bus.get_object(DBUS_BUS_NAME, DBUS_OBJECT_PATH)
            helper = dbus.Interface(proxy, DBUS_INTERFACE)
            ok, msg = helper.RestartSDDM()
            if ok:
                return True, str(msg)
        except Exception:
            pass

        return restart_sddm_service()

    @classmethod
    def scaffold_theme(
        cls,
        theme_name: str,
        base_dir: Optional[Path | str] = None,
        mode: str = "minimal",  # "minimal", "custom", "boilerplate"
        custom_wallpaper_path: Optional[str | Path] = None,
        generate_preview: bool = False,
    ) -> Tuple[bool, Optional[Path], str]:
        """
        Scaffolds a new SDDM theme in /usr/share/sddm/themes/<name>/ (or base_dir).

        Modes:
        - "minimal": Zero dummy images created. Pure QML + INI fallback gradient. (Asset-Free)
        - "custom": Copies user's chosen wallpaper and generates matching preview thumbnail.
        - "boilerplate": Provisions sample 1080p background.png and preview.png assets.
        """
        dest_base = Path(base_dir) if base_dir else Path("/usr/share/sddm/themes")
        theme_dir = dest_base / theme_name

        bg_setting = ""
        type_setting = "color"
        custom_img_path: Optional[Path] = None

        if mode == "custom" and custom_wallpaper_path:
            cand = Path(custom_wallpaper_path).resolve()
            if cand.exists():
                custom_img_path = cand
                ext = cand.suffix.lower() or ".png"
                bg_setting = f"background{ext}"
                type_setting = "image"
            else:
                mode = "minimal"

        if mode == "boilerplate":
            bg_setting = "background.png"
            type_setting = "image"

        starter_conf = (
            "[General]\n"
            f"background={bg_setting}\n"
            f"type={type_setting}\n"
            "font=Sans\n"
            "fontSize=11\n"
            "color=#c0caf5\n"
            "accentColor=#7aa2f7\n"
            "clockFormat=24h\n"
            "showClock=true\n"
            "blurRadius=0\n"
        )

        metadata_json = json.dumps(
            {"name": theme_name, "author": "Custom", "version": "1.0", "description": "Custom SDDM Theme"},
            indent=2,
        )

        metadata_desktop = (
            "[SddmGreeterTheme]\n"
            f"Name={theme_name}\n"
            "Description=Custom SDDM Theme\n"
            "Author=Custom\n"
            "Type=sddm-theme\n"
            "Version=1.0\n"
            "MainScript=Main.qml\n"
            "ConfigFile=theme.conf\n"
            "QtVersion=6\n"
        )

        # 1. Write theme.conf
        ok, msg = cls.write_file(theme_dir / "theme.conf", starter_conf)
        if not ok:
            return False, None, f"Failed to scaffold theme.conf: {msg}"

        # 2. Write metadata.desktop
        ok, msg = cls.write_file(theme_dir / "metadata.desktop", metadata_desktop)
        if not ok:
            return False, None, f"Failed to scaffold metadata.desktop: {msg}"

        # 3. Write metadata.json
        ok, msg = cls.write_file(theme_dir / "metadata.json", metadata_json)
        if not ok:
            return False, None, f"Failed to scaffold metadata.json: {msg}"

        # 4. Write Main.qml
        ok, msg = cls.write_file(theme_dir / "Main.qml", STARTER_MAIN_QML)
        if not ok:
            return False, None, f"Failed to scaffold Main.qml: {msg}"

        # 5. Asset handling based on selected mode
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            if mode == "boilerplate":
                try:
                    bg_img = generate_starter_wallpaper(theme_name, 1920, 1080)
                    preview_img = bg_img.scaled(640, 360)

                    tmp_bg = tmp_path / "background.png"
                    tmp_prev = tmp_path / "preview.png"
                    bg_img.save(str(tmp_bg))
                    preview_img.save(str(tmp_prev))

                    ok_bg, msg_bg = cls.write_binary_file(theme_dir / "background.png", tmp_bg)
                    if not ok_bg:
                        logger.warning(f"Failed to write background.png: {msg_bg}")

                    ok_prev, msg_prev = cls.write_binary_file(theme_dir / "preview.png", tmp_prev)
                    if not ok_prev:
                        logger.warning(f"Failed to write preview.png: {msg_prev}")
                except Exception as e:
                    logger.warning(f"Could not generate boilerplate images: {e}")

            elif mode == "custom" and custom_img_path:
                try:
                    # Copy custom wallpaper directly into theme directory
                    dest_bg_name = bg_setting or "background.png"
                    ok_bg, msg_bg = cls.write_binary_file(theme_dir / dest_bg_name, custom_img_path)
                    if not ok_bg:
                        logger.warning(f"Failed to copy custom wallpaper: {msg_bg}")

                    # Generate scaled thumbnail preview from custom image
                    from PySide6.QtCore import Qt
                    from PySide6.QtGui import QImage

                    qimg = QImage(str(custom_img_path))
                    if not qimg.isNull():
                        preview_img = qimg.scaled(
                            640,
                            360,
                            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                        tmp_prev = tmp_path / "preview.png"
                        preview_img.save(str(tmp_prev))
                        cls.write_binary_file(theme_dir / "preview.png", tmp_prev)
                except Exception as e:
                    logger.warning(f"Could not process custom wallpaper asset: {e}")

            elif mode == "minimal" and generate_preview:
                try:
                    # Optional lightweight thumbnail without generating 1080p background
                    prev_img = generate_starter_wallpaper(theme_name, 640, 360)
                    tmp_prev = tmp_path / "preview.png"
                    prev_img.save(str(tmp_prev))
                    cls.write_binary_file(theme_dir / "preview.png", tmp_prev)
                except Exception as e:
                    logger.warning(f"Could not generate minimal thumbnail: {e}")

        return True, theme_dir, f"Theme '{theme_name}' scaffolded successfully at {theme_dir} (mode: {mode})."
