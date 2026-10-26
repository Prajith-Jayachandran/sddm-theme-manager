"""
SDDM Theme Manager - 24-Hour Solar Time-Lapse & Live Satellite Imagery (Feature 5)
Calculates continuous 24-hour solar elevation stages (astronomical dawn, golden hour, solar noon,
sunset, dusk, midnight) and transitions SDDM wallpapers smoothly or fetches live geostationary satellite frames.
"""

import datetime
import json
import math
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CACHE_DIR = Path.home() / ".cache/sddm-theme-manager/solar"


@dataclass
class SolarPhase:
    phase_id: str
    name: str
    sun_elevation_deg: float
    sky_gradient_top: str
    sky_gradient_bottom: str
    ambient_light: float


SOLAR_PHASES = [
    ("midnight", "Midnight Cosmos", -45.0, "#050711", "#0b1021", 0.15),
    ("astronomical_dawn", "Astronomical Dawn", -18.0, "#090d24", "#1e1b4b", 0.25),
    ("nautical_dawn", "Nautical Dawn", -12.0, "#0f172a", "#312e81", 0.35),
    ("civil_dawn", "Civil Dawn", -6.0, "#1e293b", "#4338ca", 0.50),
    ("golden_hour_morning", "Golden Hour Sunrise", 2.0, "#fbbf24", "#ea580c", 0.75),
    ("morning", "Crisp Morning", 25.0, "#38bdf8", "#bae6fd", 0.90),
    ("solar_noon", "Zenith High Noon", 68.0, "#0284c7", "#e0f2fe", 1.00),
    ("afternoon", "Warm Afternoon", 40.0, "#0ea5e9", "#fef08a", 0.95),
    ("golden_hour_evening", "Golden Hour Sunset", 3.0, "#f97316", "#be123c", 0.80),
    ("civil_dusk", "Civil Dusk", -5.0, "#4c1d95", "#831843", 0.55),
    ("nautical_dusk", "Nautical Dusk", -12.0, "#1e1b4b", "#312e81", 0.35),
    ("night", "Starlit Night", -35.0, "#030712", "#0f172a", 0.20),
]


class SolarTimelapseManager:
    """Manages astronomical solar calculation, satellite imagery downloads, and QML blending."""

    @classmethod
    def calculate_solar_elevation(cls, dt: Optional[datetime.datetime] = None, lat: float = 37.77) -> float:
        """
        Approximate solar elevation angle in degrees for the given datetime and latitude.
        """
        now = dt or datetime.datetime.now()
        day_of_year = now.timetuple().tm_yday
        hour = now.hour + now.minute / 60.0

        # Solar declination approximation (Cooper's equation)
        declination = 23.45 * math.sin(math.radians(360.0 / 365.0 * (day_of_year - 81)))

        # Hour angle (0 at solar noon ~ 12:00)
        hour_angle = (hour - 12.0) * 15.0

        lat_rad = math.radians(lat)
        dec_rad = math.radians(declination)
        ha_rad = math.radians(hour_angle)

        sin_elevation = math.sin(lat_rad) * math.sin(dec_rad) + math.cos(lat_rad) * math.cos(dec_rad) * math.cos(ha_rad)
        elevation_deg = math.degrees(math.asin(max(-1.0, min(1.0, sin_elevation))))
        return elevation_deg

    @classmethod
    def get_current_solar_phase(cls, dt: Optional[datetime.datetime] = None, lat: float = 37.77) -> SolarPhase:
        """Return the closest matching solar phase descriptor."""
        now = dt or datetime.datetime.now()
        elev = cls.calculate_solar_elevation(now, lat)
        hour = now.hour + now.minute / 60.0
        is_morning = hour < 12.5

        if elev > 50.0:
            p = SOLAR_PHASES[6]  # solar_noon
        elif elev > 15.0:
            p = SOLAR_PHASES[5] if is_morning else SOLAR_PHASES[7]
        elif elev > 0.0:
            p = SOLAR_PHASES[4] if is_morning else SOLAR_PHASES[8]  # golden hour
        elif elev > -6.0:
            p = SOLAR_PHASES[3] if is_morning else SOLAR_PHASES[9]  # civil dawn/dusk
        elif elev > -12.0:
            p = SOLAR_PHASES[2] if is_morning else SOLAR_PHASES[10]  # nautical
        elif elev > -20.0:
            p = SOLAR_PHASES[1] if is_morning else SOLAR_PHASES[11]  # astronomical / night
        else:
            p = SOLAR_PHASES[0]  # midnight

        return SolarPhase(
            phase_id=p[0],
            name=p[1],
            sun_elevation_deg=round(elev, 2),
            sky_gradient_top=p[3],
            sky_gradient_bottom=p[4],
            ambient_light=p[5],
        )

    @classmethod
    def fetch_satellite_imagery(cls, satellite: str = "goes-east", timeout: int = 5) -> Tuple[bool, Path, str]:
        """
        Fetches near-real-time geostationary Earth satellite imagery.
        Uses NOAA GOES public imagery server.
        """
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cached_file = CACHE_DIR / f"{satellite}_latest.jpg"

        url = "https://cdn.star.nesdis.noaa.gov/GOES16/ABI/FD/GEOCOLOR/624x624.jpg"
        if satellite == "goes-west":
            url = "https://cdn.star.nesdis.noaa.gov/GOES18/ABI/FD/GEOCOLOR/624x624.jpg"

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SDDM-Theme-Manager/1.3"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    cached_file.write_bytes(resp.read())
                    return True, cached_file, f"Live NOAA {satellite.upper()} imagery updated."
        except Exception:
            pass

        # Return cached if exists
        if cached_file.exists():
            return True, cached_file, "Using cached satellite frame."

        # Generate a placeholder simulated satellite background if offline
        from .background import BackgroundManager
        return False, cached_file, "Satellite imagery offline; using algorithmic solar sky."

    @classmethod
    def generate_solar_wallpaper_qml(cls) -> str:
        """
        Generates dynamic SolarWallpaper.qml with smooth sky gradient transitions.
        """
        phase = cls.get_current_solar_phase()
        return f"""import QtQuick 2.15

Rectangle {{
    id: solarWallpaperRoot
    anchors.fill: parent

    property string phaseId: "{phase.phase_id}"
    property string phaseName: "{phase.name}"
    property real sunElevation: {phase.sun_elevation_deg}
    property color colorTop: "{phase.sky_gradient_top}"
    property color colorBottom: "{phase.sky_gradient_bottom}"
    property real ambientLight: {phase.ambient_light}

    gradient: Gradient {{
        GradientStop {{ position: 0.0; color: solarWallpaperRoot.colorTop }}
        GradientStop {{ position: 1.0; color: solarWallpaperRoot.colorBottom }}
    }}

    // Subtle Celestial Glow
    Rectangle {{
        width: 320
        height: 320
        radius: 160
        anchors.horizontalCenter: parent.horizontalCenter
        y: parent.height * (1.0 - (solarWallpaperRoot.sunElevation + 90.0) / 180.0) - 160
        opacity: Math.max(0.1, solarWallpaperRoot.ambientLight * 0.45)
        color: "#fef08a"

        Behavior on y {{
            NumberAnimation {{ duration: 2000; easing.type: Easing.InOutQuad }}
        }}
    }}
}}
"""
