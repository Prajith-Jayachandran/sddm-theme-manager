"""
SDDM Theme Manager - Built-in Creator Monetization ("Support the Rice") (Feature 20)
Parses creator donation links from theme metadata (GitHub Sponsors, Ko-fi, Patreon, Stripe),
embeds tip triggers in theme cards, and manages the optional local "Supporter Pro Pass".
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SUPPORTER_CONFIG_PATH = Path.home() / ".config/sddm-theme-manager/supporter_pass.json"


@dataclass
class CreatorTipInfo:
    theme_name: str
    author: str
    github_sponsors: Optional[str] = None
    kofi: Optional[str] = None
    patreon: Optional[str] = None
    custom_url: Optional[str] = None

    @property
    def has_tip_links(self) -> bool:
        return bool(self.github_sponsors or self.kofi or self.patreon or self.custom_url)

    @property
    def primary_tip_url(self) -> str:
        return self.github_sponsors or self.kofi or self.patreon or self.custom_url or ""


class CreatorMonetizationManager:
    """Manages metadata tip link discovery and Supporter Pro Pass verification."""

    @classmethod
    def parse_theme_sponsorship(cls, theme_dir: Path) -> CreatorTipInfo:
        """Parse sponsorship keys from metadata.desktop."""
        meta_file = Path(theme_dir) / "metadata.desktop"
        info = CreatorTipInfo(theme_name=theme_dir.name, author="Community Artist")

        if meta_file.exists():
            try:
                for line in meta_file.read_text(encoding="utf-8", errors="replace").splitlines():
                    line = line.strip()
                    if line.startswith("Name="):
                        info.theme_name = line.split("=", 1)[1].strip()
                    elif line.startswith("Author="):
                        info.author = line.split("=", 1)[1].strip()
                    elif line.startswith("X-SDDM-Sponsor-Github="):
                        info.github_sponsors = line.split("=", 1)[1].strip()
                    elif line.startswith("X-SDDM-Sponsor-Kofi="):
                        info.kofi = line.split("=", 1)[1].strip()
                    elif line.startswith("X-SDDM-Sponsor-Patreon="):
                        info.patreon = line.split("=", 1)[1].strip()
                    elif line.startswith("X-SDDM-Sponsor-Custom="):
                        info.custom_url = line.split("=", 1)[1].strip()
            except Exception:
                pass

        # If no explicit link in file, provide default community sponsor page if author known
        if not info.has_tip_links and info.author and info.author != "Community Artist":
            info.github_sponsors = f"https://github.com/sponsors/{info.author.lower().replace(' ', '')}"

        return info

    @classmethod
    def is_supporter_pass_active(cls) -> bool:
        """Check if local user has enabled or activated Supporter Pro Pass."""
        if SUPPORTER_CONFIG_PATH.exists():
            try:
                data = json.loads(SUPPORTER_CONFIG_PATH.read_text(encoding="utf-8"))
                return bool(data.get("is_active", False))
            except Exception:
                pass
        return True  # Default to active community tier

    @classmethod
    def set_supporter_pass(cls, active: bool = True, key: str = "COMMUNITY_PRO"):
        """Activate or deactivate Supporter Pro tier."""
        SUPPORTER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "is_active": active,
            "license_key": key,
            "perks": ["exclusive_shaders", "cloud_vcs_sync", "creator_badge"],
        }
        SUPPORTER_CONFIG_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
