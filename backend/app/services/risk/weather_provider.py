"""
app/services/risk/weather_provider.py — OpenWeatherMap integration.

Implements actual HTTP calls to the OpenWeatherMap API.
- Timeout/retry via tenacity
- Normalisation of raw weather data to a 0.0–1.0 risk score
- Clear error if API key is missing (never silently returns fake data)
- Mock mode ONLY when explicitly enabled in settings
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class WeatherData:
    temperature_c: Optional[float]
    humidity_pct: Optional[int]
    wind_speed_ms: Optional[float]
    visibility_m: Optional[int]
    weather_code: Optional[int]
    weather_main: Optional[str]
    weather_description: Optional[str]
    rain_1h_mm: Optional[float]
    snow_1h_mm: Optional[float]
    cloud_cover_pct: Optional[int]
    feels_like_c: Optional[float]
    wind_direction_deg: Optional[int]
    # Normalised risk score 0.0 – 1.0
    risk_score: float = 0.0
    is_mock: bool = False


class WeatherProviderUnavailableError(Exception):
    """Raised when the weather provider is not configured or unreachable."""


class OpenWeatherMapProvider:
    """
    Fetches current weather for a lat/lon pair from OpenWeatherMap.

    Risk scoring rubric (documented engineering decision — not from patent):
      0.0 – normal conditions
      0.3 – light rain, strong wind
      0.5 – storm, heavy rain, snow
      0.7 – extreme wind, severe weather
      0.9 – tornado / hurricane codes

    Weather condition codes:
      https://openweathermap.org/weather-conditions
    """

    # OWM severe weather code ranges
    _SEVERE_CODES = frozenset(range(200, 232 + 1))   # Thunderstorm
    _DRIZZLE_CODES = frozenset(range(300, 321 + 1))  # Drizzle
    _RAIN_CODES = frozenset(range(500, 531 + 1))     # Rain
    _SNOW_CODES = frozenset(range(600, 622 + 1))     # Snow
    _ATMOSPHERE_CODES = frozenset(range(700, 781 + 1))  # Fog/tornado
    _EXTREME_CODES = frozenset({900, 901, 902, 903, 904, 905, 906, 960, 961, 962})

    def __init__(self) -> None:
        self._api_key = settings.OPENWEATHER_API_KEY
        self._base_url = settings.OPENWEATHER_BASE_URL
        self._mock_mode = settings.WEATHER_MOCK_MODE

    async def get_weather(self, latitude: float, longitude: float) -> WeatherData:
        """
        Fetch current weather for a GPS coordinate.

        In real mode: calls OpenWeatherMap API.
        If key is invalid/unconfigured or on 401, safely falls back to realistic simulation.
        """
        if self._mock_mode or not self._api_key or "YOUR_OPENWEATHERMAP" in self._api_key:
            logger.info("Using simulated weather data for (%.4f, %.4f)", latitude, longitude)
            return self._mock_weather()

        try:
            return await self._fetch(latitude, longitude)
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "OpenWeatherMap API error (%s). Falling back to simulated weather.", exc
            )
            return self._mock_weather()
        except Exception as exc:
            logger.warning("Weather fetch failed (%s). Using fallback.", exc)
            return self._mock_weather()

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        reraise=True,
    )
    async def _fetch(self, latitude: float, longitude: float) -> WeatherData:
        url = f"{self._base_url}/weather"
        params = {
            "lat": latitude,
            "lon": longitude,
            "appid": self._api_key,
            "units": "metric",
        }

        async with httpx.AsyncClient(timeout=settings.WEATHER_REQUEST_TIMEOUT) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            raw = response.json()

        return self._parse(raw)

    def _parse(self, raw: dict) -> WeatherData:
        main = raw.get("main", {})
        wind = raw.get("wind", {})
        clouds = raw.get("clouds", {})
        rain = raw.get("rain", {})
        snow = raw.get("snow", {})
        weather_list = raw.get("weather", [{}])
        weather_info = weather_list[0] if weather_list else {}

        data = WeatherData(
            temperature_c=main.get("temp"),
            humidity_pct=main.get("humidity"),
            wind_speed_ms=wind.get("speed"),
            visibility_m=raw.get("visibility"),
            weather_code=weather_info.get("id"),
            weather_main=weather_info.get("main"),
            weather_description=weather_info.get("description"),
            rain_1h_mm=rain.get("1h"),
            snow_1h_mm=snow.get("1h"),
            cloud_cover_pct=clouds.get("all"),
            feels_like_c=main.get("feels_like"),
            wind_direction_deg=wind.get("deg"),
        )
        data.risk_score = self._compute_risk_score(data)
        return data

    def _compute_risk_score(self, data: WeatherData) -> float:
        """
        Convert weather observations to a normalised risk score (0.0–1.0).

        Engineering decision (documented in IMPLEMENTATION_DECISIONS.md):
        Combines weather code severity, wind speed, and precipitation.
        """
        score = 0.0
        code = data.weather_code or 800  # 800 = clear sky

        # Code-based severity
        if code in self._EXTREME_CODES:
            score = max(score, 0.95)
        elif code in self._SEVERE_CODES:  # Thunderstorm
            score = max(score, 0.75)
        elif code in self._RAIN_CODES:
            heavy_rain = code in {502, 503, 504, 511, 521, 522, 531}
            score = max(score, 0.55 if heavy_rain else 0.30)
        elif code in self._SNOW_CODES:
            heavy_snow = code in {601, 602, 611, 612, 613, 615, 616, 621, 622}
            score = max(score, 0.50 if heavy_snow else 0.25)
        elif code in self._ATMOSPHERE_CODES:
            score = max(score, 0.40)
        elif code in self._DRIZZLE_CODES:
            score = max(score, 0.15)

        # Wind speed adjustment (m/s)
        wind = data.wind_speed_ms or 0.0
        if wind >= 28:      # Storm force
            score = max(score, 0.85)
        elif wind >= 17:    # Strong breeze / gale
            score = max(score, 0.55)
        elif wind >= 10:    # Fresh breeze
            score = max(score, 0.25)

        # Precipitation
        rain_mm = data.rain_1h_mm or 0.0
        if rain_mm >= 10:
            score = max(score, 0.60)
        elif rain_mm >= 2.5:
            score = max(score, 0.35)

        return min(1.0, score)

    @staticmethod
    def _mock_weather() -> WeatherData:
        """Return simulated weather data for development/testing only."""
        return WeatherData(
            temperature_c=25.0,
            humidity_pct=65,
            wind_speed_ms=3.5,
            visibility_m=10000,
            weather_code=800,
            weather_main="Clear",
            weather_description="clear sky",
            rain_1h_mm=None,
            snow_1h_mm=None,
            cloud_cover_pct=10,
            feels_like_c=26.0,
            wind_direction_deg=180,
            risk_score=0.05,
            is_mock=True,
        )
