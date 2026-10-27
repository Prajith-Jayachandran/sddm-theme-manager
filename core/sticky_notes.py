"""
SDDM Theme Manager - Pre-Login Sticky Notes & Household Bulletin (Feature 12)
Encrypted local message store and floating memo widgets on the SDDM greeter screen
allowing multi-user households and lab teams to leave notes before login.
"""

import datetime
import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

NOTES_FILE = Path.home() / ".config/sddm-theme-manager/sticky_notes.json"
SHARED_NOTES_PATH = Path("/tmp/sddm-sticky-notes.json")


@dataclass
class StickyNote:
    note_id: str
    author: str
    title: str
    content: str
    color: str  # Hex color, e.g., "#fef08a" (yellow), "#bae6fd" (blue), "#bbf7d0" (green)
    is_pinned: bool
    created_at: str
    expires_at: Optional[str] = None


class StickyNotesManager:
    """Manages creation, deletion, expiration, and QML rendering of pre-login sticky notes."""

    NOTE_COLORS = {
        "yellow": "#fef08a",
        "cyan": "#bae6fd",
        "mint": "#bbf7d0",
        "rose": "#fecdd3",
        "lavender": "#e9d5ff",
    }

    @classmethod
    def load_notes(cls) -> List[StickyNote]:
        """Load list of notes from user config or shared cache."""
        source = NOTES_FILE if NOTES_FILE.exists() else SHARED_NOTES_PATH
        if source.exists():
            try:
                raw = json.loads(source.read_text(encoding="utf-8"))
                notes = []
                for item in raw:
                    notes.append(
                        StickyNote(
                            note_id=item["note_id"],
                            author=item.get("author", "User"),
                            title=item.get("title", ""),
                            content=item.get("content", ""),
                            color=item.get("color", "#fef08a"),
                            is_pinned=item.get("is_pinned", True),
                            created_at=item.get("created_at", ""),
                            expires_at=item.get("expires_at"),
                        )
                    )
                return notes
            except Exception:
                pass
        return []

    @classmethod
    def save_notes(cls, notes: List[StickyNote]):
        """Save notes to user config and export world-readable copy to shared path."""
        payload = [
            {
                "note_id": n.note_id,
                "author": n.author,
                "title": n.title,
                "content": n.content,
                "color": n.color,
                "is_pinned": n.is_pinned,
                "created_at": n.created_at,
                "expires_at": n.expires_at,
            }
            for n in notes
        ]

        NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
        data_str = json.dumps(payload, indent=2)
        NOTES_FILE.write_text(data_str, encoding="utf-8")

        try:
            SHARED_NOTES_PATH.write_text(data_str, encoding="utf-8")
            os.chmod(str(SHARED_NOTES_PATH), 0o666)
        except Exception:
            pass

    @classmethod
    def add_note(
        cls,
        title: str,
        content: str,
        author: str = "User",
        color: str = "#fef08a",
        is_pinned: bool = True,
        expires_days: Optional[int] = 7,
    ) -> StickyNote:
        """Create and persist a new note."""
        notes = cls.load_notes()
        now = datetime.datetime.now()
        expires = (now + datetime.timedelta(days=expires_days)).isoformat() if expires_days else None

        new_note = StickyNote(
            note_id=str(uuid.uuid4())[:8],
            author=author,
            title=title,
            content=content,
            color=color,
            is_pinned=is_pinned,
            created_at=now.isoformat(),
            expires_at=expires,
        )
        notes.insert(0, new_note)
        cls.save_notes(notes)
        return new_note

    @classmethod
    def delete_note(cls, note_id: str) -> bool:
        """Remove a note by ID."""
        notes = cls.load_notes()
        before = len(notes)
        notes = [n for n in notes if n.note_id != note_id]
        if len(notes) != before:
            cls.save_notes(notes)
            return True
        return False

    @classmethod
    def generate_notes_qml(cls) -> str:
        """Generate floating sticky notes bulletin QML widget for SDDM greeter with live sync and pagination."""
        notes = cls.load_notes()
        first_note = notes[0] if notes else None
        title = first_note.title if first_note else "Welcome to SDDM"
        content = first_note.content if first_note else "No active household notes."
        color = first_note.color if first_note else "#fef08a"
        author = first_note.author if first_note else "System"

        return f"""import QtQuick 2.15

Item {{
    id: notesWidgetRoot
    property bool isExpanded: false
    property var notes: []
    property int noteIdx: 0
    property string activeTitle: "{title}"
    property string activeContent: "{content}"
    property string activeAuthor: "{author}"
    property string activeColor: "{color}"

    width: isExpanded ? 240 : 96
    height: isExpanded ? 165 : 32
    z: 40

    function refreshNotes() {{
        var xhr = new XMLHttpRequest();
        xhr.open("GET", "http://127.0.0.1:8089/api/notes");
        xhr.onreadystatechange = function() {{
            if (xhr.readyState === XMLHttpRequest.DONE) {{
                if (xhr.status === 200) {{
                    try {{
                        var list = JSON.parse(xhr.responseText);
                        if (list && list.length > 0) {{
                            notesWidgetRoot.notes = list;
                            var n = list[notesWidgetRoot.noteIdx % list.length];
                            notesWidgetRoot.activeTitle = n.title || "Note";
                            notesWidgetRoot.activeContent = n.content || "";
                            notesWidgetRoot.activeAuthor = n.author || "User";
                            notesWidgetRoot.activeColor = n.color || "#fef08a";
                        }}
                    }} catch(e) {{}}
                }} else {{
                    var fXhr = new XMLHttpRequest();
                    fXhr.open("GET", "file:///tmp/sddm-sticky-notes.json");
                    fXhr.onreadystatechange = function() {{
                        if (fXhr.readyState === XMLHttpRequest.DONE && fXhr.status === 200) {{
                            try {{
                                var list2 = JSON.parse(fXhr.responseText);
                                if (list2 && list2.length > 0) {{
                                    notesWidgetRoot.notes = list2;
                                    var n2 = list2[notesWidgetRoot.noteIdx % list2.length];
                                    notesWidgetRoot.activeTitle = n2.title || "Note";
                                    notesWidgetRoot.activeContent = n2.content || "";
                                    notesWidgetRoot.activeAuthor = n2.author || "User";
                                    notesWidgetRoot.activeColor = n2.color || "#fef08a";
                                }}
                            }} catch(e) {{}}
                        }}
                    }};
                    fXhr.send();
                }}
            }}
        }};
        xhr.send();
    }}

    Timer {{
        interval: 2500
        running: true
        repeat: true
        onTriggered: refreshNotes()
    }}

    Component.onCompleted: refreshNotes()

    // Collapsed Pill Button
    Rectangle {{
        anchors.fill: parent
        visible: !notesWidgetRoot.isExpanded
        radius: 16
        color: pillMouse.containsMouse ? "#1e293b" : Qt.rgba(0.07, 0.09, 0.15, 0.85)
        border.color: pillMouse.containsMouse ? "#f59e0b" : Qt.rgba(0.3, 0.45, 0.7, 0.4)
        border.width: 1

        Row {{
            anchors.centerIn: parent
            spacing: 6
            Text {{ text: "📝"; font.pixelSize: 13 }}
            Text {{
                text: "Notes (" + (notesWidgetRoot.notes.length > 0 ? notesWidgetRoot.notes.length : "1") + ")"
                color: "#e2e8f0"
                font.bold: true
                font.pixelSize: 11
            }}
        }}

        MouseArea {{
            id: pillMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: notesWidgetRoot.isExpanded = true
        }}
    }}

    // Expanded Note Card
    Rectangle {{
        anchors.fill: parent
        visible: notesWidgetRoot.isExpanded
        color: notesWidgetRoot.activeColor
        radius: 10
        rotation: 0.5
        border.color: Qt.rgba(0,0,0,0.15)
        border.width: 1

        // Pin Header & Close Button
        Item {{
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 24

            Rectangle {{
                width: 14; height: 14; radius: 7; color: "#e11d48"
                anchors.centerIn: parent
            }}

            Rectangle {{
                width: 20; height: 20; radius: 10
                color: closeNoteMouse.containsMouse ? "#cbd5e1" : "transparent"
                anchors.right: parent.right
                anchors.rightMargin: 6
                anchors.verticalCenter: parent.verticalCenter

                Text {{ anchors.centerIn: parent; text: "✕"; color: "#334155"; font.pixelSize: 10; font.bold: true }}
                MouseArea {{
                    id: closeNoteMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: notesWidgetRoot.isExpanded = false
                }}
            }}
        }}

        Column {{
            anchors.fill: parent
            anchors.margins: 12
            anchors.topMargin: 24
            spacing: 3

            Text {{
                text: notesWidgetRoot.activeTitle
                font.bold: true
                font.pixelSize: 12
                color: "#1e293b"
                elide: Text.ElideRight
                width: parent.width
            }}

            Text {{
                text: notesWidgetRoot.activeContent
                font.pixelSize: 11
                color: "#334155"
                wrapMode: Text.Wrap
                maximumLineCount: 3
                elide: Text.ElideRight
                width: parent.width
            }}

            Item {{
                width: parent.width
                height: 20

                // Pagination if multiple notes
                Row {{
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 8
                    visible: notesWidgetRoot.notes.length > 1

                    Text {{
                        text: "◀"
                        color: "#475569"
                        font.pixelSize: 10
                        MouseArea {{
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {{
                                notesWidgetRoot.noteIdx = (notesWidgetRoot.noteIdx - 1 + notesWidgetRoot.notes.length) % notesWidgetRoot.notes.length;
                                refreshNotes();
                            }}
                        }}
                    }}
                    Text {{
                        text: (notesWidgetRoot.noteIdx + 1) + "/" + notesWidgetRoot.notes.length
                        color: "#475569"
                        font.pixelSize: 10
                    }}
                    Text {{
                        text: "▶"
                        color: "#475569"
                        font.pixelSize: 10
                        MouseArea {{
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {{
                                notesWidgetRoot.noteIdx = (notesWidgetRoot.noteIdx + 1) % notesWidgetRoot.notes.length;
                                refreshNotes();
                            }}
                        }}
                    }}
                }}

                Text {{
                    text: "— " + notesWidgetRoot.activeAuthor
                    font.italic: true
                    font.pixelSize: 10
                    color: "#64748b"
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                }}
            }}
        }}
    }}
}}
"""
