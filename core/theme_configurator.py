"""
SDDM Theme Manager - Visual Theme Configurator (Theme Tweaker Engine)
Parses, updates, and resets visual parameters in theme.conf and theme.conf.user:
Clock formats, layout alignment, blur/dim effects, typography, and controls.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .polkit import remove_path_privileged, write_file_privileged


class ThemeConfigurator:
    """Manages visual customizations inside theme.conf and theme.conf.user."""

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
        "form_position": ["formPosition", "loginPosition", "alignment", "FormPosition"],
        "blur_radius": ["blur", "blurRadius", "backgroundBlur", "BlurRadius"],
        "dim_opacity": ["dim", "dimOpacity", "dimBackground", "DimBackgroundImage"],
        "font_family": ["fontFamily", "font", "textFont", "Font"],
        "font_size": ["fontSize", "textSize", "FontSize"],
        "show_password_reveal": ["showPasswordRevealButton", "showPasswordButton"],
        "accent_color": ["accentColor", "highlightColor", "color", "AccentColour"],
    }

    @classmethod
    def read_tweaks(cls, theme_dir: Path) -> Dict[str, Any]:
        """
        Reads all active tweaks from theme.conf.user, falling back to theme.conf.
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
    def _update_conf_text(cls, original_text: str, entries_to_write: Dict[str, str]) -> str:
        """Helper to update or append keys under [General] in an existing INI-like string."""
        lines = original_text.splitlines() if original_text else []
        updated_lines = []
        in_general = False
        general_found = False
        written_keys = set()

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                if in_general:
                    for k, v in entries_to_write.items():
                        if k.lower() not in written_keys:
                            updated_lines.append(f"{k}={v}")
                            written_keys.add(k.lower())
                    in_general = False

                if stripped.lower() == "[general]":
                    in_general = True
                    general_found = True

            elif in_general and "=" in stripped:
                k, _ = stripped.split("=", 1)
                k_clean = k.strip()
                matched = False
                for target_key, val in entries_to_write.items():
                    if k_clean.lower() == target_key.lower():
                        updated_lines.append(f"{target_key}={val}")
                        written_keys.add(target_key.lower())
                        matched = True
                        break
                if matched:
                    continue

            updated_lines.append(line)

        if in_general:
            for k, v in entries_to_write.items():
                if k.lower() not in written_keys:
                    updated_lines.append(f"{k}={v}")
                    written_keys.add(k.lower())

        if not general_found:
            if updated_lines and updated_lines[-1] != "":
                updated_lines.append("")
            updated_lines.append("[General]")
            for k, v in entries_to_write.items():
                updated_lines.append(f"{k}={v}")

        return "\n".join(updated_lines).strip() + "\n"

    @classmethod
    def apply_tweaks(cls, theme_dir: Path, tweaks: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Writes visual tweaks into both theme.conf and theme.conf.user under [General].
        Guarantees that SDDM greeters load and respect the customizations.
        """
        theme_p = Path(theme_dir).resolve()
        is_system = str(theme_p).startswith("/usr")
        theme_conf = theme_p / "theme.conf"
        theme_orig = theme_p / "theme.conf.orig"
        user_conf = theme_p / "theme.conf.user"

        # Backup original theme.conf if not already present
        if theme_conf.exists() and not theme_orig.exists():
            orig_text = theme_conf.read_text(encoding="utf-8", errors="ignore")
            if is_system:
                write_file_privileged(theme_orig, orig_text)
            else:
                theme_orig.write_text(orig_text, encoding="utf-8")

        # Build entries to write (standard and theme-specific alias forms)
        entries_to_write: Dict[str, str] = {}

        if "show_clock" in tweaks:
            val_bool = "true" if tweaks["show_clock"] else "false"
            entries_to_write["showClock"] = val_bool
            entries_to_write["displayClock"] = val_bool

        if "show_seconds" in tweaks:
            entries_to_write["showSeconds"] = "true" if tweaks["show_seconds"] else "false"

        if "clock_format" in tweaks:
            entries_to_write["clockFormat"] = str(tweaks["clock_format"])

        if "form_position" in tweaks:
            pos = str(tweaks["form_position"]).lower()
            entries_to_write["formPosition"] = pos
            entries_to_write["FormPosition"] = f'"{pos}"'

        if "blur_radius" in tweaks:
            r = int(tweaks["blur_radius"])
            entries_to_write["blurRadius"] = str(r)
            entries_to_write["BlurRadius"] = f'"{r}"'
            if r > 0:
                entries_to_write["PartialBlur"] = '"true"'
            else:
                entries_to_write["PartialBlur"] = '"false"'

        if "dim_opacity" in tweaks:
            d = float(tweaks["dim_opacity"])
            entries_to_write["dimOpacity"] = f"{d:.2f}"
            entries_to_write["DimBackgroundImage"] = f'"{d:.2f}"'

        if "font_family" in tweaks and tweaks["font_family"]:
            f = str(tweaks["font_family"])
            entries_to_write["fontFamily"] = f
            entries_to_write["Font"] = f

        if "font_size" in tweaks and tweaks["font_size"]:
            s = str(tweaks["font_size"])
            entries_to_write["fontSize"] = s
            entries_to_write["FontSize"] = f'"{s}"'

        if "show_password_reveal" in tweaks:
            entries_to_write["showPasswordRevealButton"] = "true" if tweaks["show_password_reveal"] else "false"

        if "accent_color" in tweaks and tweaks["accent_color"]:
            c = str(tweaks["accent_color"])
            entries_to_write["accentColor"] = c
            entries_to_write["highlightColor"] = c
            entries_to_write["color"] = c
            entries_to_write["AccentColour"] = c

        # 1. Update theme.conf.user
        orig_user = user_conf.read_text(encoding="utf-8", errors="ignore") if user_conf.exists() else ""
        new_user = cls._update_conf_text(orig_user, entries_to_write)

        # 2. Update theme.conf
        orig_conf = theme_conf.read_text(encoding="utf-8", errors="ignore") if theme_conf.exists() else ""
        new_conf = cls._update_conf_text(orig_conf, entries_to_write)

        if is_system:
            write_file_privileged(user_conf, new_user)
            ok, msg = write_file_privileged(theme_conf, new_conf)
            return ok, msg
        else:
            try:
                user_conf.write_text(new_user, encoding="utf-8")
                theme_conf.write_text(new_conf, encoding="utf-8")
                return True, "Theme tweaks applied successfully."
            except Exception as e:
                return False, f"Failed to save tweaks: {e}"

    @classmethod
    def reset_tweaks(cls, theme_dir: Path) -> Tuple[bool, str]:
        """
        Restores theme.conf from theme.conf.orig and purges user tweak overrides.
        """
        theme_p = Path(theme_dir).resolve()
        is_system = str(theme_p).startswith("/usr")
        theme_conf = theme_p / "theme.conf"
        theme_orig = theme_p / "theme.conf.orig"
        user_conf = theme_p / "theme.conf.user"

        if theme_orig.exists():
            orig_text = theme_orig.read_text(encoding="utf-8", errors="ignore")
            if is_system:
                write_file_privileged(theme_conf, orig_text)
                remove_path_privileged(theme_orig)
            else:
                theme_conf.write_text(orig_text, encoding="utf-8")
                theme_orig.unlink(missing_ok=True)

        if user_conf.exists():
            if is_system:
                remove_path_privileged(user_conf)
            else:
                user_conf.unlink(missing_ok=True)

        return True, "Theme visual tweaks restored to default."
