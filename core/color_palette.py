"""
SDDM Theme Manager - Color Palette & Pywal Accent Extractor
Extracts dominant and accent color palettes from images using native QImage sampling,
and integrates with Pywal (~/.cache/wal/colors.json) for desktop theme coherence.
"""

import json
from pathlib import Path
from typing import List, Optional, Tuple

from PySide6.QtGui import QColor, QImage

from .polkit import write_file_privileged


class ColorPaletteManager:
    """Extracts harmonious color palettes and applies accents to theme.conf.user."""

    @classmethod
    def extract_palette(cls, image_path: Path | str, count: int = 5) -> List[str]:
        """
        Samples colors from an image using downscaled QImage pixel analysis.
        Returns a list of hex color strings (e.g. ['#1a1b26', '#7aa2f7', ...]).
        """
        p = Path(image_path).resolve()
        if not p.exists() or not p.is_file():
            return []

        img = QImage(str(p))
        if img.isNull():
            return []

        # Downscale to 48x48 for fast, robust color clustering
        thumb = img.scaled(48, 48)
        color_freq = {}

        for y in range(thumb.height()):
            for x in range(thumb.width()):
                qc = thumb.pixelColor(x, y)
                # Ignore near pure black and pure white extremes
                lightness = qc.lightness()
                if lightness < 15 or lightness > 245:
                    continue

                # Quantize RGB to 32-value bins to group similar colors
                qr = (qc.red() // 16) * 16
                qg = (qc.green() // 16) * 16
                qb = (qc.blue() // 16) * 16
                bin_key = (qr, qg, qb)
                color_freq[bin_key] = color_freq.get(bin_key, 0) + 1

        if not color_freq:
            return ["#7aa2f7", "#bb9af7", "#7dcfff", "#e0af68", "#9ece6a"]

        # Sort by frequency
        sorted_bins = sorted(color_freq.items(), key=lambda item: item[1], reverse=True)

        selected_hexes = []
        for (r, g, b), _ in sorted_bins:
            hex_code = f"#{r:02x}{g:02x}{b:02x}"
            # Check distance against already selected colors
            is_distinct = True
            for existing in selected_hexes:
                er = int(existing[1:3], 16)
                eg = int(existing[3:5], 16)
                eb = int(existing[5:7], 16)
                dist = ((r - er) ** 2 + (g - eg) ** 2 + (b - eb) ** 2) ** 0.5
                if dist < 45:  # too close in Euclidean RGB space
                    is_distinct = False
                    break

            if is_distinct:
                selected_hexes.append(hex_code)
                if len(selected_hexes) >= count:
                    break

        return selected_hexes

    @classmethod
    def get_pywal_colors(cls) -> Optional[dict]:
        """
        Reads Pywal colors cache (~/.cache/wal/colors.json) if available.
        Returns dict with 'wallpaper', 'colors': {...}, 'special': {...} or None.
        """
        wal_cache = Path.home() / ".cache" / "wal" / "colors.json"
        if not wal_cache.exists():
            return None

        try:
            data = json.loads(wal_cache.read_text(encoding="utf-8"))
            return data
        except Exception:
            return None

    @classmethod
    def apply_accent_to_theme(
        cls,
        theme_dir: Path,
        accent_hex: str,
        text_hex: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Writes accent and text colors into theme.conf.user under [General].
        Preserves all existing keys.
        """
        theme_p = Path(theme_dir).resolve()
        user_conf = theme_p / "theme.conf.user"

        lines = []
        if user_conf.exists():
            lines = user_conf.read_text(encoding="utf-8", errors="ignore").splitlines()

        # Update or add [General] section with accentColor / highlightColor
        updated_lines = []
        in_general = False
        general_found = False
        accent_added = False
        text_added = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                if in_general:
                    # Closing General section, write missing keys
                    if not accent_added:
                        updated_lines.append(f"accentColor={accent_hex}")
                        updated_lines.append(f"highlightColor={accent_hex}")
                        accent_added = True
                    if text_hex and not text_added:
                        updated_lines.append(f"fontColor={text_hex}")
                        text_added = True
                    in_general = False

                if stripped.lower() == "[general]":
                    in_general = True
                    general_found = True

            elif in_general and "=" in stripped:
                k, _ = stripped.split("=", 1)
                k_clean = k.strip().lower()
                if k_clean in ("accentcolor", "highlightcolor"):
                    updated_lines.append(f"{k.strip()}={accent_hex}")
                    accent_added = True
                    continue
                elif k_clean in ("fontcolor", "textcolor") and text_hex:
                    updated_lines.append(f"{k.strip()}={text_hex}")
                    text_added = True
                    continue

            updated_lines.append(line)

        if in_general:
            if not accent_added:
                updated_lines.append(f"accentColor={accent_hex}")
                updated_lines.append(f"highlightColor={accent_hex}")
                accent_added = True
            if text_hex and not text_added:
                updated_lines.append(f"fontColor={text_hex}")
                text_added = True

        if not general_found:
            updated_lines.append("")
            updated_lines.append("[General]")
            updated_lines.append(f"accentColor={accent_hex}")
            updated_lines.append(f"highlightColor={accent_hex}")
            if text_hex:
                updated_lines.append(f"fontColor={text_hex}")

        new_content = "\n".join(updated_lines).strip() + "\n"

        is_system = str(theme_p).startswith("/usr")
        if is_system:
            return write_file_privileged(user_conf, new_content)
        else:
            try:
                user_conf.write_text(new_content, encoding="utf-8")
                return True, "Accent color applied successfully."
            except Exception as e:
                return False, f"Failed to save accent color: {e}"
