"""
SDDM Theme Manager - Polkit & Privileged Execution Wrapper
Handles elevated operations via pkexec (or sudo fallback in --no-polkit mode).
"""

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger("sddm_theme_manager.polkit")


class PolkitConfig:
    no_polkit: bool = False
    debug: bool = False
    _warned_no_polkit: bool = False

    @classmethod
    def set_options(cls, no_polkit: bool = False, debug: bool = False):
        cls.no_polkit = no_polkit
        cls.debug = debug
        if debug:
            logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s] %(message)s")
            logger.setLevel(logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
            logger.setLevel(logging.INFO)

        if no_polkit and not cls._warned_no_polkit:
            print("[WARNING] --no-polkit flag active. Using sudo instead of pkexec for privileged operations.", file=sys.stderr)
            cls._warned_no_polkit = True


def is_sddm_installed() -> bool:
    """Check if SDDM binary or system service is present on the system."""
    if shutil.which("sddm") is not None:
        return True
    if Path("/usr/share/sddm").exists() or Path("/etc/sddm.conf.d").exists() or Path("/etc/sddm.conf").exists():
        return True
    return False


def detect_sddm_qt_version() -> Tuple[str, Optional[str]]:
    """
    Detect whether SDDM uses Qt6 or Qt5 greeter.
    Returns a tuple of (description_string, preferred_binary_path).
    """
    has_qt6 = shutil.which("sddm-greeter-qt6") is not None
    has_qt5 = shutil.which("sddm-greeter") is not None

    if has_qt6 and has_qt5:
        return "Qt6 (Qt5 fallback available)", shutil.which("sddm-greeter-qt6")
    elif has_qt6:
        return "Qt6", shutil.which("sddm-greeter-qt6")
    elif has_qt5:
        return "Qt5", shutil.which("sddm-greeter")
    else:
        return "Not found", None


def run_command(
    cmd: list[str],
    privileged: bool = False,
    input_text: Optional[str] = None,
    timeout: int = 60,
) -> Tuple[int, str, str]:
    """
    Execute a command, optionally elevating with pkexec or sudo.
    Returns (returncode, stdout, stderr).
    """
    exec_cmd = list(cmd)
    if privileged:
        if PolkitConfig.no_polkit:
            if not PolkitConfig._warned_no_polkit:
                print("[WARNING] --no-polkit flag active. Using sudo instead of pkexec.", file=sys.stderr)
                PolkitConfig._warned_no_polkit = True
            exec_cmd = ["sudo"] + exec_cmd
        else:
            exec_cmd = ["pkexec"] + exec_cmd

    if PolkitConfig.debug:
        logger.debug("Executing command: %s (input bytes: %s)", " ".join(exec_cmd), len(input_text) if input_text else 0)

    try:
        proc = subprocess.Popen(
            exec_cmd,
            stdin=subprocess.PIPE if input_text is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = proc.communicate(input=input_text, timeout=timeout)
        rc = proc.returncode

        if PolkitConfig.debug:
            logger.debug("Command finished with exit code %d", rc)
            if stdout.strip():
                logger.debug("STDOUT: %s", stdout.strip())
            if stderr.strip():
                logger.debug("STDERR: %s", stderr.strip())

        return rc, stdout, stderr
    except subprocess.TimeoutExpired:
        proc.kill()
        logger.error("Command timed out: %s", " ".join(exec_cmd))
        return -1, "", "Command timed out"
    except Exception as e:
        logger.error("Failed to execute %s: %s", " ".join(exec_cmd), e)
        return -1, "", str(e)


def write_file_privileged(filepath: str | Path, content: str) -> Tuple[bool, str]:
    """
    Write content to a file that may require root permissions.
    Uses 'pkexec /usr/bin/tee <filepath>' or 'sudo /usr/bin/tee <filepath>'.
    Ensures parent directory exists.
    """
    path = Path(filepath).resolve()
    parent = path.parent

    # If parent directory doesn't exist, create it
    if not parent.exists():
        mkdir_binary = shutil.which("mkdir") or "/usr/bin/mkdir"
        rc, out, err = run_command([mkdir_binary, "-p", str(parent)], privileged=True)
        if rc != 0:
            return False, f"Failed to create directory {parent}: {err or out}"

    tee_binary = shutil.which("tee") or "/usr/bin/tee"
    rc, out, err = run_command([tee_binary, str(path)], privileged=True, input_text=content)
    if rc == 0:
        return True, "File written successfully."
    else:
        return False, err or out or f"Write failed with exit code {rc}"


def remove_path_privileged(filepath: str | Path) -> Tuple[bool, str]:
    """
    Remove a file or directory requiring elevated permissions.
    Uses 'pkexec /usr/bin/rm -rf <filepath>'.
    """
    path = Path(filepath).resolve()
    if not path.exists():
        return True, "Path does not exist."

    rm_binary = shutil.which("rm") or "/usr/bin/rm"
    rc, out, err = run_command([rm_binary, "-rf", str(path)], privileged=True)
    if rc == 0:
        return True, "Path removed successfully."
    else:
        return False, err or out or f"Removal failed with exit code {rc}"


def copy_directory_privileged(src: str | Path, dest: str | Path) -> Tuple[bool, str]:
    """
    Copies a directory to a system destination requiring root permissions.
    Uses 'pkexec /usr/bin/cp -r <src> <dest>' and normalizes permissions.
    """
    src_p = Path(src).resolve()
    dest_p = Path(dest).resolve()
    parent = dest_p.parent

    # Ensure parent directory exists
    if not parent.exists():
        mkdir_bin = shutil.which("mkdir") or "/usr/bin/mkdir"
        rc, out, err = run_command([mkdir_bin, "-p", str(parent)], privileged=True)
        if rc != 0:
            return False, f"Failed to create parent directory {parent}: {err or out}"

    cp_bin = shutil.which("cp") or "/usr/bin/cp"
    chmod_bin = shutil.which("chmod") or "/usr/bin/chmod"

    rc, out, err = run_command([cp_bin, "-r", str(src_p), str(dest_p)], privileged=True)
    if rc != 0:
        return False, err or out or f"Failed to copy to {dest_p}"

    # Normalize permissions so sddm daemon can read all files
    run_command([chmod_bin, "-R", "a+rX", str(dest_p)], privileged=True)
    return True, "Directory copied successfully."


def copy_file_privileged(src: str | Path, dest: str | Path) -> Tuple[bool, str]:
    """
    Copies a single file to a destination requiring elevated permissions.
    """
    src_p = Path(src).resolve()
    dest_p = Path(dest).resolve()
    parent = dest_p.parent

    if not parent.exists():
        mkdir_bin = shutil.which("mkdir") or "/usr/bin/mkdir"
        rc, out, err = run_command([mkdir_bin, "-p", str(parent)], privileged=True)
        if rc != 0:
            return False, f"Failed to create parent directory {parent}: {err or out}"

    cp_bin = shutil.which("cp") or "/usr/bin/cp"
    chmod_bin = shutil.which("chmod") or "/usr/bin/chmod"

    rc, out, err = run_command([cp_bin, "-f", str(src_p), str(dest_p)], privileged=True)
    if rc != 0:
        return False, err or out or f"Failed to copy file to {dest_p}"

    run_command([chmod_bin, "0644", str(dest_p)], privileged=True)
    return True, "File copied successfully."


def restart_sddm_service() -> Tuple[bool, str]:
    """
    Restart the sddm.service using systemctl.
    Polkit rule handles this via org.freedesktop.systemd1.manage-units or pkexec.
    """
    systemctl_bin = shutil.which("systemctl") or "/usr/bin/systemctl"
    rc, out, err = run_command([systemctl_bin, "restart", "sddm"], privileged=True)
    if rc == 0:
        return True, "SDDM service restarted."
    else:
        return False, err or out or f"Failed to restart SDDM (exit code {rc})"
