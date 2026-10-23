"""
SDDM Theme Manager - Visual Theme Configurator (Theme Tweaker Engine)
Parses, updates, and resets visual parameters in theme.conf.user:
Clock formats, layout alignment, blur/dim effects, typography, and controls.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .polkit import write_file_privileged


class ThemeConfigurator:
    """Manages visual customizations inside theme.conf.user without modifying base theme.conf."""

    DEFAULT_TWEAKS: Dict[str, Any] = {
        "clock_format": "24h",
        "show_clock": True,
        "show_seconds": False,
        "form_position": "center",
        "blur_radius": 0,
        "dim_opacity": 0.0,
        "font_family": "sans-serif",
        "font_size": 11,
        "show_password_reveal": True,
        "accent_color": "",
    }

    # Common key aliases across various SDDM theme QML scripts
    KEY_MAP = {
        "clock_format": ["type", "timeFormat", "clockFormat"],
        "show_clock": ["showClock", "displayClock", "clockEnabled"],
        "show_seconds": ["showSeconds", "displaySeconds"],
        "form_position": ["formPosition", "loginPosition", "alignment"],
        "blur_radius": ["blur", "blurRadius", "backgroundBlur"],
        "dim_opacity": ["dim", "dimOpacity", "dimBackground"],
        "font_family": ["fontFamily", "font", "textFont"],
        "font_size": ["fontSize", "textSize"],
        "show_password_reveal": ["showPasswordRevealButton", "showPasswordButton"],
        "accent_color": ["accentColor", "highlightColor"],
    }

    @classmethod
    def read_tweaks(cls, theme_dir: Path) -> Dict[str, Any]:
        """
        Reads all active tweaks from theme.conf.user (falling back to theme.conf).
        """
        theme_p = Path(theme_dir).resolve()
        base_conf = theme_p / "theme.conf"
        user_conf = theme_p / "theme.conf.user"

        raw_data: Dict[str, str] = {}

        for conf_file in [base_conf, user_conf]:
            if conf_file.exists():
                lines = conf_file.read_text(encoding="utf-8", errors="ignore").splitlines()
                in_general = False
                for line in lines:
                    line = line.strip()
                    if line.startswith("[") and line.endswith("]"):
                        in_general = (line.lower() == "[general]")
                    elif in_general and "=" in line:
                        k, v = line.split("=", 1)
                        raw_data[k.strip().lower()] = v.strip().strip('"\'')

        result = dict(cls.DEFAULT_TWEAKS)

        # Map raw keys into normalized tweaks
        for tweak_key, aliases in cls.KEY_MAP.items():
            for alias in aliases:
                val = raw_data.get(alias.lower())
                if val is not None:
                    if tweak_key in ("show_clock", "show_seconds", "show_password_reveal"):
                        result[tweak_key] = val.lower() in ("true", "1", "yes")
                    elif tweak_key in ("blur_radius", "font_size"):
                        try:
                            result[tweak_key] = int(float(val))
                        except ValueError:
                            pass
                    elif tweak_key == "dim_opacity":
                        try:
                            result[tweak_key] = float(val)
                        except ValueError:
                            pass
                    else:
                        result[tweak_key] = val
                    break

        return result

    @classmethod
    def apply_tweaks(cls, theme_dir: Path, tweaks: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Writes visual tweaks into theme.conf.user under [General].
        Preserves existing user overrides (like custom background).
        """
        theme_p = Path(theme_dir).resolve()
        user_conf = theme_p / "theme.conf.user"

        lines = []
        if user_conf.exists():
            lines = user_conf.read_text(encoding="utf-8", errors="ignore").splitlines()

        # Build entries to write
        entries_to_write = {}
        if "show_clock" in tweaks:
            entries_to_write["showClock"] = "true" if tweaks["show_clock"] else "false"
        if "show_seconds" in tweaks:
            entries_to_write["showSeconds"] = "true" if tweaks["show_seconds"] else "false"
        if "clock_format" in tweaks:
            entries_to_write["clockFormat"] = tweaks["clock_format"]
        if "form_position" in tweaks:
            entries_to_write["formPosition"] = tweaks["form_position"]
        if "blur_radius" in tweaks:
            entries_to_write["blurRadius"] = str(tweaks["blur_radius"])
        if "dim_opacity" in tweaks:
            entries_to_write["dimOpacity"] = f"{tweaks['dim_opacity']:.2f}"
        if "font_family" in tweaks and tweaks["font_family"]:
            entries_to_write["fontFamily"] = tweaks["font_family"]
        if "font_size" in tweaks and tweaks["font_size"]:
            entries_to_write["fontSize"] = str(tweaks["font_size"])
        if "show_password_reveal" in tweaks:
            entries_to_write["showPasswordRevealButton"] = "true" if tweaks["show_password_reveal"] else "false"
        if "accent_color" in tweaks and tweaks["accent_color"]:
            entries_to_write["accentColor"] = tweaks["accent_color"]
            entries_to_write["highlightColor"] = tweaks["accent_color"]

        updated_lines = []
        in_general = False
        general_found = False
        written_keys = set()

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                if in_general:
                    # Write any remaining keys
                    for k, v in entries_to_write.items():
                        if k not in written_keys:
                            updated_lines.append(f"{k}={v}")
                            written_keys.add(k)
                    in_general = False

                if stripped.lower() == "[general]":
                    in_general = True
                    general_found = True

            elif in_general and "=" in stripped:
                k, _ = stripped.split("=", 1)
                k_clean = k.strip()
                # Check if this line matches any of our target keys
                matched = False
                for target_key, val in entries_to_write.items():
                    if k_clean.lower() == target_key.lower():
                        updated_lines.append(f"{target_key}={val}")
                        written_keys.add(target_key)
                        matched = True
                        break
                if matched:
                    continue

            updated_lines.append(line)

        if in_general:
            for k, v in entries_to_write.items():
                if k not in written_keys:
                    updated_lines.append(f"{k}={v}")
                    written_keys.add(k)

        if not general_found:
            updated_lines.append("")
            updated_lines.append("[General]")
            for k, v in entries_to_write.items():
                updated_lines.append(f"{k}={v}")

        new_content = "\n".join(updated_lines).strip() + "\n"

        is_system = str(theme_p).startswith("/usr")
        if is_system:
            return write_file_privileged(user_conf, new_content)
        else:
            try:
                user_conf.write_text(new_content, encoding="utf-8")
                return True, "Theme tweaks applied successfully."
            except Exception as e:
                return False, f"Failed to save tweaks: {e}"
