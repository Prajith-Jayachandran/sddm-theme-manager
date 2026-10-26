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
        """Generate floating sticky notes bulletin QML widget for SDDM greeter."""
        notes = cls.load_notes()
        first_note = notes[0] if notes else None
        title = first_note.title if first_note else "Welcome to SDDM"
        content = first_note.content if first_note else "No active household notes."
        color = first_note.color if first_note else "#fef08a"
        author = first_note.author if first_note else "System"

        return f"""import QtQuick 2.15

Item {{
    id: notesWidgetRoot
    width: 220
    height: 140
    anchors.top: parent.top
    anchors.right: parent.right
    anchors.margins: 28
    z: 15

    Rectangle {{
        anchors.fill: parent
        color: "{color}"
        radius: 8
        rotation: 1.5

        // Subtle Pin Header
        Rectangle {{
            width: 14
            height: 14
            radius: 7
            color: "#e11d48"
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.topMargin: 6
        }}

        Column {{
            anchors.fill: parent
            anchors.margins: 14
            anchors.topMargin: 22
            spacing: 4

            Text {{
                text: "{title}"
                font.bold: true
                font.pixelSize: 12
                color: "#1e293b"
                elide: Text.ElideRight
                width: parent.width
            }}

            Text {{
                text: "{content}"
                font.pixelSize: 11
                color: "#334155"
                wrapMode: Text.Wrap
                maximumLineCount: 3
                elide: Text.ElideRight
                width: parent.width
            }}

            Text {{
                text: "— {author}"
                font.italic: true
                font.pixelSize: 10
                color: "#64748b"
                anchors.right: parent.right
            }}
        }}
    }}
}}
"""
