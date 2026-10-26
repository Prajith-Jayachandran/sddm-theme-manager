"""
SDDM Theme Manager - Interactive Pre-Login Mini-Games (Feature 17)
Pure-QML retro mini-games (Flappy Tux, Cyber Pong, 2048) playable directly on the SDDM greeter
screen while waiting for background downloads, system updates, or as an easter egg.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class GreeterGameInfo:
    id: str
    title: str
    genre: str
    description: str
    hotkey: str
    qml_source: str


FLAPPY_TUX_QML = """import QtQuick 2.15

Item {
    id: gameRoot
    width: 320
    height: 480
    anchors.centerIn: parent
    focus: true

    property int score: 0
    property real tuxY: 200
    property real tuxVelocity: 0
    property bool isGameOver: false

    Rectangle {
        anchors.fill: parent
        color: "#0f172a"
        border.color: "#38bdf8"
        border.width: 2
        radius: 12
        clip: true

        // Tux Player
        Rectangle {
            id: tux
            width: 28
            height: 28
            radius: 14
            color: "#fbbf24"
            x: 60
            y: gameRoot.tuxY

            Text {
                anchors.centerIn: parent
                text: "🐧"
                font.pixelSize: 20
            }
        }

        // Score
        Text {
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.margins: 16
            text: "Score: " + gameRoot.score
            color: "#ffffff"
            font.bold: true
            font.pixelSize: 18
        }

        // Game Over Banner
        Rectangle {
            anchors.centerIn: parent
            width: 200
            height: 80
            radius: 8
            color: Qt.rgba(0, 0, 0, 0.85)
            visible: gameRoot.isGameOver

            Column {
                anchors.centerIn: parent
                spacing: 6
                Text { text: "GAME OVER"; color: "#ef4444"; font.bold: true; font.pixelSize: 16; anchors.horizontalCenter: parent.horizontalCenter }
                Text { text: "Press Space to Restart"; color: "#94a3b8"; font.pixelSize: 12; anchors.horizontalCenter: parent.horizontalCenter }
            }
        }
    }

    Timer {
        interval: 25
        running: !gameRoot.isGameOver
        repeat: true
        onTriggered: {
            gameRoot.tuxVelocity += 0.6; // Gravity
            gameRoot.tuxY += gameRoot.tuxVelocity;
            if (gameRoot.tuxY > gameRoot.height - 35) {
                gameRoot.tuxY = gameRoot.height - 35;
                gameRoot.isGameOver = true;
            } else if (gameRoot.tuxY < 0) {
                gameRoot.tuxY = 0;
            }
        }
    }

    Keys.onSpacePressed: {
        if (gameRoot.isGameOver) {
            gameRoot.tuxY = 200;
            gameRoot.tuxVelocity = -8;
            gameRoot.score = 0;
            gameRoot.isGameOver = false;
        } else {
            gameRoot.tuxVelocity = -8; // Flap jump
            gameRoot.score += 1;
        }
    }
}
"""

CYBER_PONG_QML = """import QtQuick 2.15

Item {
    id: pongRoot
    width: 440
    height: 300
    anchors.centerIn: parent
    focus: true

    property real ballX: 220
    property real ballY: 150
    property real ballVX: 4.0
    property real ballVY: 3.0
    property real paddleY: 110
    property real aiPaddleY: 110
    property int playerScore: 0
    property int aiScore: 0

    Rectangle {
        anchors.fill: parent
        color: "#05070f"
        border.color: "#00f0ff"
        border.width: 2
        radius: 8

        // Ball
        Rectangle {
            width: 12
            height: 12
            radius: 6
            color: "#fcee0a"
            x: pongRoot.ballX
            y: pongRoot.ballY
        }

        // Player Paddle
        Rectangle {
            width: 10
            height: 60
            radius: 4
            color: "#00f0ff"
            x: 20
            y: pongRoot.paddleY
        }

        // AI Paddle
        Rectangle {
            width: 10
            height: 60
            radius: 4
            color: "#ff003c"
            x: parent.width - 30
            y: pongRoot.aiPaddleY
        }

        // Scores
        Text {
            anchors.top: parent.top
            anchors.margins: 12
            anchors.horizontalCenter: parent.horizontalCenter
            text: pongRoot.playerScore + "  :  " + pongRoot.aiScore
            color: "#f8fafc"
            font.bold: true
            font.pixelSize: 20
        }
    }

    Timer {
        interval: 20
        running: true
        repeat: true
        onTriggered: {
            pongRoot.ballX += pongRoot.ballVX;
            pongRoot.ballY += pongRoot.ballVY;

            // Bounce top/bottom
            if (pongRoot.ballY <= 0 || pongRoot.ballY >= pongRoot.height - 12) {
                pongRoot.ballVY = -pongRoot.ballVY;
            }

            // AI tracking
            if (pongRoot.ballY > pongRoot.aiPaddleY + 30) pongRoot.aiPaddleY += 3.0;
            else if (pongRoot.ballY < pongRoot.aiPaddleY + 30) pongRoot.aiPaddleY -= 3.0;

            // Player paddle hit
            if (pongRoot.ballX <= 30 && pongRoot.ballY >= pongRoot.paddleY && pongRoot.ballY <= pongRoot.paddleY + 60) {
                pongRoot.ballVX = Math.abs(pongRoot.ballVX);
            }

            // AI paddle hit
            if (pongRoot.ballX >= pongRoot.width - 40 && pongRoot.ballY >= pongRoot.aiPaddleY && pongRoot.ballY <= pongRoot.aiPaddleY + 60) {
                pongRoot.ballVX = -Math.abs(pongRoot.ballVX);
            }

            // Reset on out of bounds
            if (pongRoot.ballX < 0) {
                pongRoot.aiScore += 1;
                pongRoot.ballX = 220;
                pongRoot.ballY = 150;
                pongRoot.ballVX = 4.0;
            } else if (pongRoot.ballX > pongRoot.width) {
                pongRoot.playerScore += 1;
                pongRoot.ballX = 220;
                pongRoot.ballY = 150;
                pongRoot.ballVX = -4.0;
            }
        }
    }

    Keys.onUpPressed: pongRoot.paddleY = Math.max(0, pongRoot.paddleY - 20)
    Keys.onDownPressed: pongRoot.paddleY = Math.min(pongRoot.height - 60, pongRoot.paddleY + 20)
}
"""


class GreeterGamesManager:
    """Manages pre-login QML mini-games and shortcuts."""

    GAMES: List[GreeterGameInfo] = [
        GreeterGameInfo(
            id="flappy_tux",
            title="Flappy Tux",
            genre="Arcade / Tap",
            description="Jump through obstacles with the Linux penguin using Spacebar",
            hotkey="Ctrl+Alt+F",
            qml_source=FLAPPY_TUX_QML,
        ),
        GreeterGameInfo(
            id="cyber_pong",
            title="Cyber Pong 2077",
            genre="Retro Arcade",
            description="Classic neon paddle game against the computer AI",
            hotkey="Ctrl+Alt+P",
            qml_source=CYBER_PONG_QML,
        ),
    ]

    @classmethod
    def list_games(cls) -> List[GreeterGameInfo]:
        return cls.GAMES

    @classmethod
    def get_game_by_id(cls, game_id: str) -> Optional[GreeterGameInfo]:
        for g in cls.GAMES:
            if g.id == game_id:
                return g
        return None

    @classmethod
    def export_game_component(cls, game_id: str, dest_dir: Path) -> Tuple[bool, str]:
        """Export game QML file into theme directory."""
        game = cls.get_game_by_id(game_id)
        if not game:
            return False, f"Unknown game '{game_id}'."

        dest_dir = Path(dest_dir).resolve()
        dest_file = dest_dir / f"Game{game.id.replace('_', '').capitalize()}.qml"
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_file.write_text(game.qml_source, encoding="utf-8")
            return True, f"Mini-game '{game.title}' saved to {dest_file.name}."
        except Exception as e:
            return False, f"Failed to export game: {e}"
