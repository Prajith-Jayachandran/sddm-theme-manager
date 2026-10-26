"""
SDDM Theme Manager - SDDM Boot Chime & Audio Synthesizer (Feature 2)
Direct low-level audio playback and procedural sound synthesis for SDDM greeter.
Zero external audio binary dependencies for generation; supports PipeWire, PulseAudio, and ALSA.
"""

import json
import math
import os
import shutil
import struct
import subprocess
import wave
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .polkit import run_command, write_file_privileged

SOUNDS_DIR = Path.home() / ".local/share/sddm-theme-manager/sounds"
CONFIG_FILE = Path.home() / ".config/sddm-theme-manager/audio_config.json"
SYSTEM_XSETUP = Path("/usr/share/sddm/scripts/Xsetup")
SYSTEM_SOUNDS_DIR = Path("/usr/share/sddm/sounds")


class AudioSynthesizer:
    """Generates pure mathematically synthesized PCM WAV audio without external assets."""

    @classmethod
    def synthesize_sine_chord(cls, frequencies: List[float], duration_sec: float, sample_rate: int = 44100) -> bytes:
        """Synthesize a polyphonic decaying harmonic sine chord."""
        num_samples = int(duration_sec * sample_rate)
        data = bytearray()
        for i in range(num_samples):
            t = float(i) / sample_rate
            decay = math.exp(-2.5 * t / duration_sec)
            sample_val = 0.0
            for f in frequencies:
                sample_val += math.sin(2.0 * math.pi * f * t)
            sample_val = (sample_val / len(frequencies)) * decay * 0.8
            # 16-bit signed PCM
            ival = int(max(-32767, min(32767, sample_val * 32767)))
            # Stereo (duplicate to 2 channels)
            data += struct.pack("<hh", ival, ival)
        return bytes(data)

    @classmethod
    def create_wav_file(cls, output_path: Path, pcm_bytes: bytes, sample_rate: int = 44100):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output_path), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_bytes)


class AudioChimeManager:
    """Manages boot chimes, user input audio feedback, and SDDM startup audio hooks."""

    PRESETS = {
        "ps2_synth": {
            "name": "PlayStation 2 Ambient",
            "desc": "Deep harmonic synth sweep with resonant sustain",
            "notes": [110.0, 164.81, 220.0, 329.63],  # A2, E3, A3, E4
            "duration": 3.2,
        },
        "mac_retro": {
            "name": "Macintosh Platinum Chime",
            "desc": "Crisp, bright major triad with warm decay",
            "notes": [261.63, 329.63, 392.0, 523.25],  # C4, E4, G4, C5
            "duration": 2.4,
        },
        "win98_ambient": {
            "name": "Windows 98 Ambient Wave",
            "desc": "Nostalgic electronic atmospheric startup tone",
            "notes": [196.0, 246.94, 293.66, 392.0, 440.0],  # G3, B3, D4, G4, A4
            "duration": 2.8,
        },
        "glados_cyber": {
            "name": "Cybernetic Voice Beep",
            "desc": "Futuristic two-tone high-frequency biometric acknowledge",
            "notes": [440.0, 880.0, 1320.0],
            "duration": 0.8,
        },
        "mech_click": {
            "name": "Mechanical Switch Click",
            "desc": "Tactile switch audio feedback for keyboard input",
            "notes": [800.0, 1600.0, 2400.0],
            "duration": 0.08,
        },
    }

    @classmethod
    def ensure_preset_sound(cls, preset_id: str) -> Path:
        """Synthesize and cache preset WAV file if not already present."""
        info = cls.PRESETS.get(preset_id, cls.PRESETS["mac_retro"])
        wav_path = SOUNDS_DIR / f"{preset_id}.wav"
        if not wav_path.exists():
            pcm = AudioSynthesizer.synthesize_sine_chord(
                frequencies=info["notes"],
                duration_sec=info["duration"],
            )
            AudioSynthesizer.create_wav_file(wav_path, pcm)
        return wav_path

    @classmethod
    def find_audio_player(cls) -> Optional[List[str]]:
        """Find the best available command-line audio player on the system."""
        if shutil.which("pw-play"):
            return ["pw-play"]
        if shutil.which("paplay"):
            return ["paplay"]
        if shutil.which("aplay"):
            return ["aplay", "-q"]
        if shutil.which("canberra-gtk-play"):
            return ["canberra-gtk-play", "-f"]
        return None

    @classmethod
    def play_chime(cls, preset_id: str) -> Tuple[bool, str]:
        """Test-play the chime using the host system's audio server."""
        player = cls.find_audio_player()
        if not player:
            return False, "No audio player found (pw-play, paplay, or aplay). Please install PipeWire or ALSA utils."

        wav_path = cls.ensure_preset_sound(preset_id)
        try:
            cmd = player + [str(wav_path)]
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, f"Playing '{preset_id}' chime via {player[0]}."
        except Exception as e:
            return False, f"Failed to play sound: {e}"

    @classmethod
    def load_config(cls) -> dict:
        if CONFIG_FILE.exists():
            try:
                return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"enabled": False, "preset": "mac_retro", "volume": 80}

    @classmethod
    def save_config(cls, conf: dict):
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(conf, indent=2), encoding="utf-8")

    @classmethod
    def install_sddm_chime_hook(cls, preset_id: str) -> Tuple[bool, str]:
        """
        Installs the sound into /usr/share/sddm/sounds/ and adds a non-blocking
        playback hook to SDDM's /usr/share/sddm/scripts/Xsetup.
        """
        wav_path = cls.ensure_preset_sound(preset_id)
        dest_wav = SYSTEM_SOUNDS_DIR / f"{preset_id}.wav"

        # 1. Copy sound to system sounds directory
        mkdir_bin = shutil.which("mkdir") or "/usr/bin/mkdir"
        run_command([mkdir_bin, "-p", str(SYSTEM_SOUNDS_DIR)], privileged=True)

        cp_bin = shutil.which("cp") or "/usr/bin/cp"
        rc, out, err = run_command([cp_bin, str(wav_path), str(dest_wav)], privileged=True)
        if rc != 0:
            return False, f"Failed to copy sound to system: {err or out}"

        chmod_bin = shutil.which("chmod") or "/usr/bin/chmod"
        run_command([chmod_bin, "644", str(dest_wav)], privileged=True)

        # 2. Add hook to /usr/share/sddm/scripts/Xsetup
        hook_cmd = f"(pw-play {dest_wav} || paplay {dest_wav} || aplay -q {dest_wav}) >/dev/null 2>&1 &"
        hook_tag = "# SDDM-THEME-MANAGER-CHIME"

        existing = ""
        if SYSTEM_XSETUP.exists():
            try:
                existing = SYSTEM_XSETUP.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass

        # Strip old hook if exists
        lines = [l for l in existing.splitlines() if hook_tag not in l]
        lines.append(f"{hook_cmd} {hook_tag}")
        new_content = "\n".join(lines) + "\n"

        ok, msg = write_file_privileged(str(SYSTEM_XSETUP), new_content, mode="0755")
        if not ok:
            return False, f"Failed to write Xsetup hook: {msg}"

        cls.save_config({"enabled": True, "preset": preset_id, "volume": 80})
        return True, f"Boot chime '{preset_id}' successfully installed into SDDM Xsetup hook."

    @classmethod
    def remove_sddm_chime_hook(cls) -> Tuple[bool, str]:
        """Removes the chime hook from /usr/share/sddm/scripts/Xsetup."""
        hook_tag = "# SDDM-THEME-MANAGER-CHIME"
        if not SYSTEM_XSETUP.exists():
            cls.save_config({"enabled": False, "preset": "mac_retro", "volume": 80})
            return True, "No Xsetup hook present."

        try:
            existing = SYSTEM_XSETUP.read_text(encoding="utf-8", errors="replace")
            lines = [l for l in existing.splitlines() if hook_tag not in l]
            new_content = "\n".join(lines) + "\n"
            ok, msg = write_file_privileged(str(SYSTEM_XSETUP), new_content, mode="0755")
            if not ok:
                return False, f"Failed to update Xsetup: {msg}"
            cls.save_config({"enabled": False, "preset": "mac_retro", "volume": 80})
            return True, "Boot chime hook removed from SDDM Xsetup."
        except Exception as e:
            return False, f"Error removing hook: {e}"
