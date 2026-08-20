"""
Weather via Open-Meteo (free, no API key). Home coordinates are read from
the `preferences` table under the key "home_location", set via
PUT /preferences/home_location with a body like {"value": {"lat": 32.9857, "lon": -96.7503}}.
"""

import requests
from sqlalchemy.orm import Session

import preferences_service

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

_WEATHER_CODES = {
    0: "Clear sky", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Dense drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow",
    80: "Light rain showers", 81: "Rain showers", 82: "Violent rain showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}


def get_home_location(db: Session) -> dict | None:
    return preferences_service.get_preference(db, "home_location")


def get_current_weather(db: Session) -> dict:
    location = get_home_location(db)
    if not location or "lat" not in location or "lon" not in location:
        raise RuntimeError(
            "No home_location set. PUT /preferences/home_location with "
            '{"value": {"lat": <latitude>, "lon": <longitude>}} first.'
        )

    resp = requests.get(
        OPEN_METEO_URL,
        params={
            "latitude": location["lat"],
            "longitude": location["lon"],
            "current": "temperature_2m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,weather_code",
            "temperature_unit": "celsius",
            "timezone": "auto",
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    current = data.get("current", {})
    daily = data.get("daily", {})

    current_code = current.get("weather_code")
    return {
        "current_temp_c": current.get("temperature_2m"),
        "current_condition": _WEATHER_CODES.get(current_code, "Unknown"),
        "high_temp_c": (daily.get("temperature_2m_max") or [None])[0],
        "low_temp_c": (daily.get("temperature_2m_min") or [None])[0],
    }
