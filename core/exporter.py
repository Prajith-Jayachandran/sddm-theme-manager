"""
SDDM Theme Manager - 1-Click Theme Backup, Export & Sharing
Creates shareable theme archives (.tar.gz / .tar.zst) bundling custom wallpapers,
theme.conf.user overrides, and metadata manifests for easy community exchange.
"""

import datetime
import json
import shutil
import subprocess
import tarfile
from pathlib import Path
from typing import Optional, Tuple

from .installer import ThemeInstaller
from .theme_scanner import ThemeScanner


class ThemeExporter:
    """Exports and imports portable SDDM theme bundles."""

    BUNDLE_MANIFEST_NAME = "manifest.json"

    @classmethod
    def export_theme_bundle(cls, theme_dir: Path | str, output_path: Path | str) -> Tuple[bool, str]:
        """
        Packs the theme folder into an archive (.tar.gz or .tar.zst).
        """
        src = Path(theme_dir).resolve()
        dest = Path(output_path).resolve()

        if not src.exists() or not src.is_dir():
            return False, f"Theme directory not found: {src}"

        if not ThemeScanner.is_valid_theme_dir(src):
            return False, f"Directory does not appear to be a valid SDDM theme: {src.name}"

        # Ensure parent folder exists
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Temporary work folder to package manifest
        import tempfile
        with tempfile.TemporaryDirectory(prefix="sddm_export_") as temp_dir:
            temp_path = Path(temp_dir)
            stage_dir = temp_path / src.name
            shutil.copytree(src, stage_dir, symlinks=True)

            # Generate manifest
            manifest = {
                "format": "sddm-theme-bundle",
                "version": "1.0",
                "theme_id": src.name,
                "exported_at": datetime.datetime.now().isoformat(),
            }
            manifest_file = stage_dir / cls.BUNDLE_MANIFEST_NAME
            manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

            # Check if zstd is requested and available
            if dest.name.endswith(".zst") and shutil.which("tar") and shutil.which("zstd"):
                try:
                    res = subprocess.run(
                        ["tar", "--zstd", "-cf", str(dest), "-C", str(temp_path), src.name],
                        capture_output=True,
                        text=True,
                    )
                    if res.returncode == 0:
                        return True, f"Exported theme bundle to {dest}"
                except Exception:
                    pass

            # Standard tar.gz fallback
            gz_dest = dest if dest.name.endswith((".tar.gz", ".tgz")) else dest.with_suffix(".tar.gz")
            try:
                with tarfile.open(str(gz_dest), "w:gz") as tar:
                    tar.add(str(stage_dir), arcname=src.name)
                return True, f"Exported theme bundle to {gz_dest}"
            except Exception as e:
                return False, f"Failed to create theme archive: {e}"

    @classmethod
    def import_theme_bundle(
        cls,
        bundle_path: Path | str,
        dest_base: Optional[Path | str] = None,
    ) -> Tuple[bool, Optional[Path], str]:
        """
        Installs an exported theme archive into system SDDM folder using ThemeInstaller.
        """
        p = Path(bundle_path).resolve()
        if not p.exists() or not p.is_file():
            return False, None, f"Bundle file not found: {p}"

        # Delegate to ThemeInstaller
        return ThemeInstaller.install_from_archive(p, dest_base=dest_base)
