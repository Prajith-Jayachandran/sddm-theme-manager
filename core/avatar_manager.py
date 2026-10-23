"""
SDDM Theme Manager - User Avatar / Profile Picture Manager
Configures user profile avatars for SDDM greeters across both SDDM faces
(/usr/share/sddm/faces/<user>.face.icon), legacy (~/.face.icon),
and modern AccountsService (/var/lib/AccountsService/icons/<user>) locations.
"""

import getpass
import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

from .polkit import copy_file_privileged, run_command, write_file_privileged


class AvatarManager:
    """Manages user avatar images for SDDM login screens."""

    @classmethod
    def get_current_username(cls) -> str:
        """Returns the current logged-in username."""
        return os.environ.get("USER") or getpass.getuser()

    @classmethod
    def get_system_users(cls) -> List[str]:
        """Returns regular human users on the system (UID >= 1000)."""
        users = []
        try:
            with open("/etc/passwd", "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split(":")
                    if len(parts) >= 6:
                        name, _, uid, _, _, home, _ = parts[:7]
                        try:
                            uid_num = int(uid)
                            if 1000 <= uid_num < 60000 and name != "nobody" and Path(home).exists():
                                users.append(name)
                        except ValueError:
                            pass
        except Exception:
            pass

        cur = cls.get_current_username()
        if cur not in users:
            users.insert(0, cur)
        return users

    @classmethod
    def get_user_avatar(cls, username: Optional[str] = None) -> Optional[Path]:
        """
        Locates existing avatar for a user checking SDDM faces, AccountsService, or ~/.face.icon.
        """
        user = username or cls.get_current_username()

        # 1. Check SDDM native faces folder (/usr/share/sddm/faces/<user>.face.icon)
        sddm_face = Path(f"/usr/share/sddm/faces/{user}.face.icon")
        if sddm_face.exists() and sddm_face.stat().st_size > 0:
            return sddm_face

        # 2. Check AccountsService
        acc_icon = Path(f"/var/lib/AccountsService/icons/{user}")
        if acc_icon.exists() and acc_icon.stat().st_size > 0:
            return acc_icon

        # 3. Check user's home ~/.face.icon or ~/.face
        home = Path.home() if user == cls.get_current_username() else Path(f"/home/{user}")
        for fname in [".face.icon", ".face"]:
            candidate = home / fname
            if candidate.exists() and candidate.stat().st_size > 0:
                return candidate

        return None

    @classmethod
    def set_user_avatar(
        cls,
        image_path: Path | str,
        username: Optional[str] = None,
        crop_square: bool = True,
    ) -> Tuple[bool, str]:
        """
        Scales/crops the image and sets it as user avatar in /usr/share/sddm/faces/,
        ~/.face.icon, and AccountsService.
        """
        user = username or cls.get_current_username()
        src_p = Path(image_path).resolve()
        if not src_p.exists() or not src_p.is_file():
            return False, f"Image file not found: {src_p}"

        img = QImage(str(src_p))
        if img.isNull():
            return False, "Failed to load image file."

        # Crop to square if requested
        if crop_square:
            w, h = img.width(), img.height()
            min_dim = min(w, h)
            x_offset = (w - min_dim) // 2
            y_offset = (h - min_dim) // 2
            img = img.copy(x_offset, y_offset, min_dim, min_dim)

        # Scale to standard 256x256
        avatar_img = img.scaled(256, 256, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

        # 1. Save unprivileged copy to ~/.face.icon
        home = Path.home() if user == cls.get_current_username() else Path(f"/home/{user}")
        user_face = home / ".face.icon"
        try:
            avatar_img.save(str(user_face), "PNG")
            os.chmod(user_face, 0o644)
        except Exception:
            pass

        # 2. Prepare temp file for privileged copies
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            avatar_img.save(str(tmp_path), "PNG")

        try:
            # 3. Copy to SDDM faces directory (/usr/share/sddm/faces/<user>.face.icon)
            sddm_face_dir = Path("/usr/share/sddm/faces")
            run_command(["/usr/bin/mkdir", "-p", str(sddm_face_dir)], privileged=True)
            sddm_face_dest = sddm_face_dir / f"{user}.face.icon"
            sddm_ok, _ = copy_file_privileged(tmp_path, sddm_face_dest)
            if sddm_ok:
                run_command(["/usr/bin/chmod", "0644", str(sddm_face_dest)], privileged=True)

            # 4. Copy to AccountsService icons
            acc_dir = Path("/var/lib/AccountsService/icons")
            run_command(["/usr/bin/mkdir", "-p", str(acc_dir)], privileged=True)
            acc_icon_dest = acc_dir / user
            acc_ok, _ = copy_file_privileged(tmp_path, acc_icon_dest)
            if acc_ok:
                run_command(["/usr/bin/chmod", "0644", str(acc_icon_dest)], privileged=True)

            # 5. Update /var/lib/AccountsService/users/<user>
            acc_users_dir = Path("/var/lib/AccountsService/users")
            run_command(["/usr/bin/mkdir", "-p", str(acc_users_dir)], privileged=True)
            acc_user_file = acc_users_dir / user
            user_conf_content = (
                "[User]\n"
                f"Icon={acc_icon_dest}\n"
            )
            if acc_user_file.exists():
                try:
                    old_content = acc_user_file.read_text(encoding="utf-8", errors="ignore")
                    if "[User]" in old_content:
                        lines = []
                        icon_written = False
                        for l in old_content.splitlines():
                            if l.strip().lower().startswith("icon="):
                                lines.append(f"Icon={acc_icon_dest}")
                                icon_written = True
                            else:
                                lines.append(l)
                        if not icon_written:
                            lines.append(f"Icon={acc_icon_dest}")
                        user_conf_content = "\n".join(lines).strip() + "\n"
                except Exception:
                    pass

            write_file_privileged(acc_user_file, user_conf_content)
        finally:
            tmp_path.unlink(missing_ok=True)

        return True, f"User avatar for '{user}' updated successfully!"
