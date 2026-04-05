from __future__ import annotations

from typing import Any

import requests


class WeatherServiceError(Exception):
    pass


class WeatherService:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.geo_url = "http://api.openweathermap.org/geo/1.0/direct"
        self.weather_url = "https://api.openweathermap.org/data/2.5/weather"

    def get_weather_by_location(self, location: str) -> dict[str, Any]:
        if not self.api_key:
            raise WeatherServiceError("OpenWeatherMap API key is missing.")

        geo_response = requests.get(
            self.geo_url,
            params={"q": location, "limit": 1, "appid": self.api_key},
            timeout=15,
        )
        geo_response.raise_for_status()
        geo_payload = geo_response.json()

        if not geo_payload:
            raise WeatherServiceError("Location not found in weather service.")

        resolved = geo_payload[0]
        lat = resolved["lat"]
        lon = resolved["lon"]

        weather_response = requests.get(
            self.weather_url,
            params={"lat": lat, "lon": lon, "appid": self.api_key, "units": "metric"},
            timeout=15,
        )
        weather_response.raise_for_status()
        weather_payload = weather_response.json()

        rainfall_mm = 0.0
        if "rain" in weather_payload:
            rainfall_mm = float(
                weather_payload["rain"].get("1h", weather_payload["rain"].get("3h", 0.0))
            )

        return {
            "resolved_name": f"{resolved.get('name', '')}, {resolved.get('state', resolved.get('country', ''))}".strip(", "),
            "state": resolved.get("state"),
            "country": resolved.get("country"),
            "coordinates": {"lat": lat, "lon": lon},
            "temperature_c": float(weather_payload["main"]["temp"]),
            "humidity_percent": float(weather_payload["main"]["humidity"]),
            "rainfall_mm": rainfall_mm,
            "source": "openweathermap",
        }

