"""
SDDM Theme Manager - Real-Time Weather & Astronomical Cosmos (Feature 3)
Connects to Open-Meteo API (no API key required) and astronomical solar/lunar algorithms
to render weather overlays (raindrops, snowflakes, starry cosmos, moon phases) on SDDM greeters.
"""

import datetime
import json
import math
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple


@dataclass
class WeatherData:
    temperature: float
    unit: str
    condition_code: int
    condition_text: str
    is_day: bool
    precipitation: float
    wind_speed: float
    moon_phase: str
    moon_illumination: float
    updated_at: str


WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

MOON_PHASES = [
    "New Moon",
    "Waxing Crescent",
    "First Quarter",
    "Waxing Gibbous",
    "Full Moon",
    "Waning Gibbous",
    "Last Quarter",
    "Waning Crescent",
]


class WeatherService:
    """Fetches real-time meteorology and computes astronomical coordinates."""

    DEFAULT_CACHE_PATH = Path.home() / ".cache/sddm-theme-manager/weather.json"

    @classmethod
    def calculate_moon_phase(cls, date: Optional[datetime.date] = None) -> Tuple[str, float]:
        """
        Calculates the moon phase and approximate illumination percentage using Julian Date.
        Returns (phase_name, illumination_ratio 0.0-1.0).
        """
        d = date or datetime.date.today()
        year = d.year
        month = d.month
        day = d.day

        if month < 3:
            year -= 1
            month += 12

        a = year // 100
        b = a // 4
        c = 2 - a + b
        e = int(365.25 * (year + 4716))
        f = int(30.6001 * (month + 1))
        jd = c + day + e + f - 1524.5

        # Days since known new moon (Jan 6, 2000)
        days_since_new = jd - 2451549.5
        synodic_month = 29.53058867
        cycle_position = (days_since_new / synodic_month) % 1.0

        phase_index = int(cycle_position * 8) % 8
        phase_name = MOON_PHASES[phase_index]

        # Illumination calculation: 0 at new moon, 1 at full moon
        illumination = (1.0 - math.cos(cycle_position * 2.0 * math.pi)) / 2.0
        return phase_name, round(illumination, 2)

    @classmethod
    def fetch_weather(cls, latitude: float = 37.7749, longitude: float = -122.4194, timeout: int = 4) -> WeatherData:
        """
        Fetches current weather from Open-Meteo REST API.
        Falls back to local cache or realistic default simulation if offline.
        """
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={latitude}&longitude={longitude}&current=temperature_2m,relative_humidity_2m,"
            f"weather_code,precipitation,wind_speed_10m,is_day"
        )

        moon_phase, illumination = cls.calculate_moon_phase()

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SDDM-Theme-Manager/1.3"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    curr = data.get("current", {})
                    code = curr.get("weather_code", 0)
                    weather = WeatherData(
                        temperature=curr.get("temperature_2m", 20.0),
                        unit=data.get("current_units", {}).get("temperature_2m", "°C"),
                        condition_code=code,
                        condition_text=WEATHER_CODES.get(code, "Clear"),
                        is_day=bool(curr.get("is_day", 1)),
                        precipitation=curr.get("precipitation", 0.0),
                        wind_speed=curr.get("wind_speed_10m", 0.0),
                        moon_phase=moon_phase,
                        moon_illumination=illumination,
                        updated_at=datetime.datetime.now().isoformat(),
                    )
                    cls._save_cache(weather)
                    return weather
        except Exception:
            pass

        # Try cache
        cached = cls._load_cache()
        if cached:
            return cached

        # Simulated fallback
        now = datetime.datetime.now()
        is_day = 6 <= now.hour < 20
        return WeatherData(
            temperature=21.5,
            unit="°C",
            condition_code=0,
            condition_text="Clear sky (Simulated)",
            is_day=is_day,
            precipitation=0.0,
            wind_speed=5.2,
            moon_phase=moon_phase,
            moon_illumination=illumination,
            updated_at=now.isoformat(),
        )

    @classmethod
    def _save_cache(cls, data: WeatherData):
        try:
            cls.DEFAULT_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "temperature": data.temperature,
                "unit": data.unit,
                "condition_code": data.condition_code,
                "condition_text": data.condition_text,
                "is_day": data.is_day,
                "precipitation": data.precipitation,
                "wind_speed": data.wind_speed,
                "moon_phase": data.moon_phase,
                "moon_illumination": data.moon_illumination,
                "updated_at": data.updated_at,
            }
            cls.DEFAULT_CACHE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            pass

    @classmethod
    def _load_cache(cls) -> Optional[WeatherData]:
        if cls.DEFAULT_CACHE_PATH.exists():
            try:
                p = json.loads(cls.DEFAULT_CACHE_PATH.read_text(encoding="utf-8"))
                return WeatherData(
                    temperature=p["temperature"],
                    unit=p["unit"],
                    condition_code=p["condition_code"],
                    condition_text=p["condition_text"],
                    is_day=p["is_day"],
                    precipitation=p["precipitation"],
                    wind_speed=p["wind_speed"],
                    moon_phase=p["moon_phase"],
                    moon_illumination=p["moon_illumination"],
                    updated_at=p["updated_at"],
                )
            except Exception:
                pass
        return None

    @classmethod
    def generate_weather_qml(cls, weather: WeatherData) -> str:
        """
        Generate standalone WeatherCanvas.qml widget with particle animations
        and astronomical moon phase badge.
        """
        is_rain = weather.condition_code in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95]
        is_snow = weather.condition_code in [71, 73, 75, 77, 85, 86]
        particle_type = "rain" if is_rain else ("snow" if is_snow else "stars")

        return f"""import QtQuick 2.15

Item {{
    id: weatherRoot
    anchors.fill: parent
    z: 10

    property string weatherType: "{particle_type}"
    property string conditionText: "{weather.condition_text}"
    property real temperature: {weather.temperature}
    property string moonPhase: "{weather.moon_phase}"
    property real moonIllumination: {weather.moon_illumination}

    // Weather Telemetry Capsule (Top-Left)
    Rectangle {{
        id: weatherPill
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.margins: 24
        width: weatherRow.implicitWidth + 32
        height: 42
        radius: 21
        color: Qt.rgba(0.08, 0.09, 0.14, 0.75)
        border.color: Qt.rgba(0.3, 0.4, 0.6, 0.4)
        border.width: 1

        Row {{
            id: weatherRow
            anchors.centerIn: parent
            spacing: 12

            Text {{
                text: weatherRoot.weatherType === "rain" ? "🌧️" : (weatherRoot.weatherType === "snow" ? "❄️" : "✨")
                font.pixelSize: 18
                verticalAlignment: Text.AlignVCenter
            }}

            Text {{
                text: weatherRoot.temperature + "°C • " + weatherRoot.conditionText
                color: "#e2e8f0"
                font.pixelSize: 13
                font.bold: true
                verticalAlignment: Text.AlignVCenter
            }}

            Text {{
                text: "🌙 " + weatherRoot.moonPhase
                color: "#94a3b8"
                font.pixelSize: 12
                verticalAlignment: Text.AlignVCenter
            }}
        }}
    }}

    // Dynamic Weather Canvas Particle Animator
    Canvas {{
        id: particleCanvas
        anchors.fill: parent
        renderTarget: Canvas.FramebufferObject

        property var particles: []

        Component.onCompleted: {{
            var count = weatherRoot.weatherType === "rain" ? 80 : (weatherRoot.weatherType === "snow" ? 60 : 45);
            for (var i = 0; i < count; i++) {{
                particles.push({{
                    x: Math.random() * width,
                    y: Math.random() * height,
                    speed: Math.random() * 3 + 2,
                    size: Math.random() * 2.5 + 1.0,
                    alpha: Math.random() * 0.6 + 0.3
                }});
            }}
            animTimer.start();
        }}

        onPaint: {{
            var ctx = getContext("2d");
            ctx.clearRect(0, 0, width, height);

            if (weatherRoot.weatherType === "rain") {{
                ctx.strokeStyle = Qt.rgba(0.6, 0.8, 1.0, 0.5);
                ctx.lineWidth = 1.5;
                ctx.beginPath();
                for (var r = 0; r < particles.length; r++) {{
                    var p = particles[r];
                    ctx.moveTo(p.x, p.y);
                    ctx.lineTo(p.x - 1, p.y + p.size * 8);
                }}
                ctx.stroke();
            }} else if (weatherRoot.weatherType === "snow") {{
                ctx.fillStyle = Qt.rgba(1.0, 1.0, 1.0, 0.7);
                for (var s = 0; s < particles.length; s++) {{
                    var snow = particles[s];
                    ctx.beginPath();
                    ctx.arc(snow.x, snow.y, snow.size, 0, 2 * Math.PI);
                    ctx.fill();
                }}
            }} else {{
                // Twinkling celestial stars
                ctx.fillStyle = Qt.rgba(0.9, 0.95, 1.0, 0.6);
                for (var st = 0; st < particles.length; st++) {{
                    var star = particles[st];
                    ctx.beginPath();
                    ctx.arc(star.x, star.y, star.size * 0.8, 0, 2 * Math.PI);
                    ctx.fill();
                }}
            }}
        }}

        Timer {{
            id: animTimer
            interval: 33
            repeat: true
            onTriggered: {{
                for (var i = 0; i < particleCanvas.particles.length; i++) {{
                    var p = particleCanvas.particles[i];
                    p.y += p.speed;
                    if (weatherRoot.weatherType === "snow") {{
                        p.x += Math.sin(p.y * 0.05) * 0.5;
                    }}
                    if (p.y > particleCanvas.height) {{
                        p.y = 0;
                        p.x = Math.random() * particleCanvas.width;
                    }}
                }}
                particleCanvas.requestPaint();
            }}
        }}
    }}
}}
"""
