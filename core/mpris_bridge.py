"""
SDDM Theme Manager - Pre-Login MPRIS Media Capsule (Feature 4)
Connects to system DBus (org.mpris.MediaPlayer2.*) to display and control active media
(Spotify, Firefox, VLC, MPD) from the SDDM greeter before logging into the desktop.
"""

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SHARED_STATUS_PATH = Path("/tmp/sddm-mpris.json")


@dataclass
class MediaTrackInfo:
    player_name: str
    title: str
    artist: str
    album: str
    art_url: str
    status: str  # "Playing", "Paused", "Stopped"
    can_control: bool


class MPRISBridge:
    """Discovers MPRIS players, extracts metadata, issues commands, and renders SDDM capsule."""

    @classmethod
    def get_active_players(cls) -> List[str]:
        """Query DBus for running MPRIS2 media player services."""
        qdbus = shutil.which("qdbus") or shutil.which("qdbus-qt6")
        if qdbus:
            try:
                res = subprocess.run([qdbus], capture_output=True, text=True, timeout=2)
                if res.returncode == 0:
                    return [
                        line.strip()
                        for line in res.stdout.splitlines()
                        if line.strip().startswith("org.mpris.MediaPlayer2.")
                    ]
            except Exception:
                pass

        # Fallback to playerctl if available
        if shutil.which("playerctl"):
            try:
                res = subprocess.run(["playerctl", "-l"], capture_output=True, text=True, timeout=2)
                if res.returncode == 0:
                    return [f"org.mpris.MediaPlayer2.{p.strip()}" for p in res.stdout.splitlines() if p.strip()]
            except Exception:
                pass

        return []

    @classmethod
    def get_current_track(cls) -> MediaTrackInfo:
        """
        Retrieves current track metadata. Falls back to cached shared file
        if running directly under the isolated SDDM greeter session.
        """
        # 1. Try playerctl first if present
        if shutil.which("playerctl"):
            try:
                status_res = subprocess.run(["playerctl", "status"], capture_output=True, text=True, timeout=2)
                status = status_res.stdout.strip() if status_res.returncode == 0 else "Paused"

                meta_res = subprocess.run(
                    ["playerctl", "metadata", "--format", "{{artist}}///{{title}}///{{album}}///{{mpris:artUrl}}"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if meta_res.returncode == 0 and meta_res.stdout.strip():
                    parts = meta_res.stdout.strip().split("///")
                    track = MediaTrackInfo(
                        player_name="Media Player",
                        artist=parts[0] or "Unknown Artist",
                        title=parts[1] if len(parts) > 1 and parts[1] else "No Track Playing",
                        album=parts[2] if len(parts) > 2 else "",
                        art_url=parts[3] if len(parts) > 3 else "",
                        status=status,
                        can_control=True,
                    )
                    cls.export_shared_status(track)
                    return track
            except Exception:
                pass

        # 2. Try shared status file (for greeter)
        cached = cls.read_shared_status()
        if cached:
            return cached

        # 3. Default standby track info
        standby = MediaTrackInfo(
            player_name="System Audio",
            title="Desktop Audio Ready",
            artist="SDDM Media Capsule",
            album="System",
            art_url="",
            status="Paused",
            can_control=False,
        )
        cls.export_shared_status(standby)
        return standby

    @classmethod
    def export_shared_status(cls, track: MediaTrackInfo):
        """Export status to world-readable JSON so SDDM greeter can display it."""
        try:
            payload = {
                "player_name": track.player_name,
                "title": track.title,
                "artist": track.artist,
                "album": track.album,
                "art_url": track.art_url,
                "status": track.status,
                "can_control": track.can_control,
            }
            SHARED_STATUS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            os.chmod(str(SHARED_STATUS_PATH), 0o666)
        except Exception:
            pass

    @classmethod
    def read_shared_status(cls) -> Optional[MediaTrackInfo]:
        """Read media metadata from shared greeter cache."""
        if SHARED_STATUS_PATH.exists():
            try:
                p = json.loads(SHARED_STATUS_PATH.read_text(encoding="utf-8"))
                return MediaTrackInfo(
                    player_name=p.get("player_name", "Media Player"),
                    title=p.get("title", ""),
                    artist=p.get("artist", ""),
                    album=p.get("album", ""),
                    art_url=p.get("art_url", ""),
                    status=p.get("status", "Paused"),
                    can_control=p.get("can_control", True),
                )
            except Exception:
                pass
        return None

    @classmethod
    def play_pause(cls) -> Tuple[bool, str]:
        """Toggle playback state."""
        if shutil.which("playerctl"):
            subprocess.run(["playerctl", "play-pause"], capture_output=True, timeout=2)
            return True, "Toggled play-pause."
        return False, "playerctl not available."

    @classmethod
    def next_track(cls) -> Tuple[bool, str]:
        """Skip to next media track."""
        if shutil.which("playerctl"):
            subprocess.run(["playerctl", "next"], capture_output=True, timeout=2)
            return True, "Skipped to next track."
        return False, "playerctl not available."

    @classmethod
    def previous_track(cls) -> Tuple[bool, str]:
        """Return to previous media track."""
        if shutil.which("playerctl"):
            subprocess.run(["playerctl", "previous"], capture_output=True, timeout=2)
            return True, "Returned to previous track."
        return False, "playerctl not available."

    @classmethod
    def generate_capsule_qml(cls) -> str:
        """
        Generate dynamic island / capsule QML widget for SDDM greeter with working playback controls.
        """
        return """import QtQuick 2.15

Item {
    id: mediaCapsuleRoot
    width: capsuleRect.width
    height: capsuleRect.height
    z: 30

    property string trackTitle: "Ready"
    property string trackArtist: "No media active"
    property string playStatus: "Paused"

    function sendCmd(cmdName) {
        if (cmdName === "play-pause") {
            mediaCapsuleRoot.playStatus = (mediaCapsuleRoot.playStatus === "Playing" ? "Paused" : "Playing");
        }
        var xhr = new XMLHttpRequest();
        xhr.open("POST", "http://127.0.0.1:8089/api/mpris/" + cmdName);
        xhr.send();
    }

    function refreshMpris() {
        var xhr = new XMLHttpRequest();
        xhr.open("GET", "http://127.0.0.1:8089/api/mpris");
        xhr.onreadystatechange = function() {
            if (xhr.readyState === XMLHttpRequest.DONE) {
                if (xhr.status === 200) {
                    try {
                        var data = JSON.parse(xhr.responseText);
                        if (data.title) mediaCapsuleRoot.trackTitle = data.title;
                        if (data.artist) mediaCapsuleRoot.trackArtist = data.artist;
                        if (data.status) mediaCapsuleRoot.playStatus = data.status;
                    } catch(e) {}
                } else {
                    var fXhr = new XMLHttpRequest();
                    fXhr.open("GET", "file:///tmp/sddm-mpris.json");
                    fXhr.onreadystatechange = function() {
                        if (fXhr.readyState === XMLHttpRequest.DONE && fXhr.status === 200) {
                            try {
                                var data2 = JSON.parse(fXhr.responseText);
                                if (data2.title) mediaCapsuleRoot.trackTitle = data2.title;
                                if (data2.artist) mediaCapsuleRoot.trackArtist = data2.artist;
                                if (data2.status) mediaCapsuleRoot.playStatus = data2.status;
                            } catch(e) {}
                        }
                    };
                    fXhr.send();
                }
            }
        };
        xhr.send();
    }

    Timer {
        interval: 1200
        running: true
        repeat: true
        onTriggered: refreshMpris()
    }

    Component.onCompleted: refreshMpris()

    Rectangle {
        id: capsuleRect
        width: Math.min(360, contentRow.implicitWidth + 28)
        height: 38
        radius: 19
        color: Qt.rgba(0.06, 0.08, 0.12, 0.90)
        border.color: Qt.rgba(0.3, 0.45, 0.7, 0.40)
        border.width: 1

        Row {
            id: contentRow
            anchors.centerIn: parent
            spacing: 10

            // Vinyl / Album Disc Icon
            Rectangle {
                width: 24
                height: 24
                radius: 12
                color: "#1e1e2e"
                border.color: "#89b4fa"
                border.width: 1
                anchors.verticalCenter: parent.verticalCenter

                Text {
                    anchors.centerIn: parent
                    text: "🎵"
                    font.pixelSize: 12
                }

                RotationAnimation on rotation {
                    from: 0
                    to: 360
                    duration: 5000
                    loops: Animation.Infinite
                    running: mediaCapsuleRoot.playStatus === "Playing"
                }
            }

            // Track & Artist Column
            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 1

                Text {
                    id: txtTitle
                    text: mediaCapsuleRoot.trackTitle
                    color: "#f8fafc"
                    font.bold: true
                    font.pixelSize: 11
                    elide: Text.ElideRight
                    width: 130
                }

                Text {
                    id: txtArtist
                    text: mediaCapsuleRoot.trackArtist
                    color: "#94a3b8"
                    font.pixelSize: 9
                    elide: Text.ElideRight
                    width: 130
                }
            }

            // Media Control Action Buttons
            Row {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 4

                Rectangle {
                    width: 24; height: 24; radius: 12
                    color: prevMouse.containsMouse ? "#334155" : "transparent"
                    anchors.verticalCenter: parent.verticalCenter
                    Text { anchors.centerIn: parent; text: "⏮"; color: "#cbd5e1"; font.pixelSize: 12 }
                    MouseArea {
                        id: prevMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: sendCmd("previous")
                    }
                }

                Rectangle {
                    width: 26; height: 26; radius: 13
                    color: playMouse.containsMouse ? "#0284c7" : "#0369a1"
                    anchors.verticalCenter: parent.verticalCenter
                    Text {
                        anchors.centerIn: parent
                        text: mediaCapsuleRoot.playStatus === "Playing" ? "⏸" : "▶"
                        color: "#ffffff"
                        font.bold: true
                        font.pixelSize: 13
                    }
                    MouseArea {
                        id: playMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: sendCmd("play-pause")
                    }
                }

                Rectangle {
                    width: 24; height: 24; radius: 12
                    color: nextMouse.containsMouse ? "#334155" : "transparent"
                    anchors.verticalCenter: parent.verticalCenter
                    Text { anchors.centerIn: parent; text: "⏭"; color: "#cbd5e1"; font.pixelSize: 12 }
                    MouseArea {
                        id: nextMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: sendCmd("next")
                    }
                }
            }
        }
    }
}
"""
