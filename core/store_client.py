"""
SDDM Theme Manager - KDE Store / OCS Client
Queries OpenDesktop / KDE Store API for SDDM themes, retrieves metadata,
previews, and downloads packages directly to user storage.
"""

import os
import tempfile
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from .installer import ThemeInstaller

OCS_BASE_URL = "https://api.pling.com/ocs/v1"
SDDM_CATEGORY_ID = "101"
USER_AGENT = "SDDM-Theme-Manager/1.0 (Linux; DE-Agnostic)"


@dataclass
class StoreItem:
    id: str
    name: str
    author: str
    version: str
    description: str
    preview_url: str
    downloads: str
    score: str


class StoreClient:
    """Client for browsing and downloading SDDM themes from KDE Store / OpenDesktop."""

    @classmethod
    def fetch_themes(
        cls,
        page: int = 1,
        page_size: int = 16,
        search_query: str = "",
        sort_by: str = "latest",  # latest, high, down
    ) -> Tuple[bool, List[StoreItem], str]:
        """
        Fetches a list of SDDM themes from the store.
        Returns (success, list_of_items, message).
        """
        params = {
            "categories": SDDM_CATEGORY_ID,
            "page": str(page),
            "pagesize": str(page_size),
        }
        if search_query.strip():
            params["search"] = search_query.strip()
        if sort_by in ("latest", "high", "down"):
            params["sort"] = sort_by

        query_str = urllib.parse.urlencode(params)
        url = f"{OCS_BASE_URL}/content/data?{query_str}"

        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=12) as response:
                xml_data = response.read()

            root = ET.fromstring(xml_data)
            items: List[StoreItem] = []

            for content in root.findall(".//content"):
                c_id = cls._get_node_text(content, "id")
                name = cls._get_node_text(content, "name") or "Unnamed Theme"
                author = cls._get_node_text(content, "personid") or "Unknown"
                version = cls._get_node_text(content, "version") or ""
                desc = cls._get_node_text(content, "description") or ""
                preview = (
                    cls._get_node_text(content, "previewpic1")
                    or cls._get_node_text(content, "smallpreviewpic1")
                    or cls._get_node_text(content, "previewpic2")
                    or cls._get_node_text(content, "previewpic")
                    or cls._get_node_text(content, "smallpreviewpic")
                    or ""
                )
                downloads = cls._get_node_text(content, "downloads") or "0"
                score = cls._get_node_text(content, "score") or "0"

                if c_id:
                    items.append(
                        StoreItem(
                            id=c_id,
                            name=name,
                            author=author,
                            version=version,
                            description=cls._clean_html(desc),
                            preview_url=preview,
                            downloads=downloads,
                            score=score,
                        )
                    )

            return True, items, f"Retrieved {len(items)} themes."
        except urllib.error.URLError as e:
            return False, [], f"Network error connecting to store: {e}"
        except Exception as e:
            return False, [], f"Failed to retrieve themes: {e}"

    @classmethod
    def get_download_url(cls, item_id: str, file_index: int = 1) -> Tuple[bool, Optional[str], str]:
        """Retrieves direct download URL for a theme package."""
        url = f"{OCS_BASE_URL}/content/download/{item_id}/{file_index}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=12) as response:
                xml_data = response.read()

            root = ET.fromstring(xml_data)
            link_node = root.find(".//downloadlink")
            if link_node is not None and link_node.text:
                return True, link_node.text.strip(), "Download link found."

            return False, None, "No download link available for this item."
        except Exception as e:
            return False, None, f"Failed to get download URL: {e}"

    @classmethod
    def download_and_install(
        cls,
        item: StoreItem,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Tuple[bool, Optional[Path], str]:
        """
        Downloads theme archive from store and installs it into ~/.local/share/sddm/themes/.
        """
        success, dl_url, msg = cls.get_download_url(item.id)
        if not success or not dl_url:
            return False, None, msg

        # Download to a temporary file
        try:
            req = urllib.request.Request(dl_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as resp:
                total_size = resp.getheader("Content-Length")
                total = int(total_size) if total_size else 0

                # Guess file extension from response url or disposition
                parsed_url = urllib.parse.urlparse(dl_url)
                filename = os.path.basename(parsed_url.path)
                if not filename or "." not in filename:
                    filename = f"theme_{item.id}.tar.gz"

                with tempfile.NamedTemporaryFile(delete=False, suffix="_" + filename) as tf:
                    temp_filepath = Path(tf.name)
                    downloaded = 0
                    chunk_size = 16384
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        tf.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total > 0:
                            progress_callback(downloaded, total)

            # Install directly into /usr/share/sddm/themes/ with elevated permissions
            try:
                inst_ok, path, inst_msg = ThemeInstaller.install_from_archive(temp_filepath)
                if inst_ok and path and item.preview_url:
                    preview_file = path / "preview.png"
                    if not preview_file.exists():
                        try:
                            p_req = urllib.request.Request(item.preview_url, headers={"User-Agent": USER_AGENT})
                            with urllib.request.urlopen(p_req, timeout=10) as p_resp:
                                preview_bytes = p_resp.read()
                                if preview_bytes:
                                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as p_tmp:
                                        p_tmp.write(preview_bytes)
                                        p_tmp_path = Path(p_tmp.name)
                                    from .polkit import run_command
                                    run_command(["cp", str(p_tmp_path), str(preview_file)], privileged=True)
                                    run_command(["chmod", "644", str(preview_file)], privileged=True)
                                    p_tmp_path.unlink(missing_ok=True)
                        except Exception:
                            pass

                return inst_ok, path, inst_msg
            finally:
                if temp_filepath.exists():
                    temp_filepath.unlink(missing_ok=True)

        except Exception as e:
            return False, None, f"Download failed: {e}"

    @staticmethod
    def _get_node_text(parent: ET.Element, tag: str) -> str:
        elem = parent.find(tag)
        if elem is not None and elem.text:
            return elem.text.strip()
        return ""

    @staticmethod
    def _clean_html(raw_html: str) -> str:
        """Strips HTML tags for clean display."""
        import re

        clean = re.sub(r"<[^<]+?>", "", raw_html)
        return clean.strip()
