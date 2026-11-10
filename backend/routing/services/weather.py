"""Hourly forecast lookup from Open-Meteo (no API key), batched and cached."""
from dataclasses import dataclass
from datetime import datetime, timezone

import requests
from django.conf import settings
from django.core.cache import cache

from .risk import Weather

BATCH_SIZE = 50
FORECAST_DAYS = 7
COORD_PRECISION = 2  # ~1 km; also the dedupe key for the cache


class WeatherError(Exception):
    pass


@dataclass(frozen=True)
class HourlyForecast:
    start: datetime  # UTC time of index 0
    wind_mph: list[float]
    rain_in_hr: list[float]
    snow_in_hr: list[float]

    def at(self, when: datetime) -> tuple[Weather, bool]:
        """Weather for the hour nearest `when`; bool is False if `when` is outside the forecast."""
        hours = round((when - self.start).total_seconds() / 3600)
        in_range = 0 <= hours < len(self.wind_mph)
        i = min(max(hours, 0), len(self.wind_mph) - 1)
        return Weather(self.wind_mph[i], self.rain_in_hr[i], self.snow_in_hr[i]), in_range


def _key(lat: float, lon: float) -> str:
    return f"wx:{round(lat, COORD_PRECISION)}:{round(lon, COORD_PRECISION)}"


def _num(v) -> float:
    return float(v) if v is not None else 0.0


def _fetch_batch(points: list[tuple[float, float]]) -> list[HourlyForecast]:
    params = {
        "latitude": ",".join(f"{lat:.{COORD_PRECISION}f}" for lat, _ in points),
        "longitude": ",".join(f"{lon:.{COORD_PRECISION}f}" for _, lon in points),
        "hourly": "wind_speed_10m,rain,snowfall",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "forecast_days": FORECAST_DAYS,
        "timezone": "UTC",
    }
    try:
        resp = requests.get(settings.OPEN_METEO_URL, params=params, timeout=settings.HTTP_TIMEOUT_SECONDS)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise WeatherError(f"Weather service unavailable: {exc}") from exc

    payload = resp.json()
    results = payload if isinstance(payload, list) else [payload]
    forecasts = []
    for item in results:
        hourly = item["hourly"]
        start = datetime.fromisoformat(hourly["time"][0]).replace(tzinfo=timezone.utc)
        forecasts.append(
            HourlyForecast(
                start=start,
                wind_mph=[_num(v) for v in hourly["wind_speed_10m"]],
                rain_in_hr=[_num(v) for v in hourly["rain"]],
                snow_in_hr=[_num(v) for v in hourly["snowfall"]],
            )
        )
    return forecasts


def get_forecasts(points: list[tuple[float, float]]) -> list[HourlyForecast]:
    """Forecast for each point (same order). Points that round to the same grid cell share a call."""
    keys = [_key(lat, lon) for lat, lon in points]
    found: dict[str, HourlyForecast] = cache.get_many(set(keys))

    missing: dict[str, tuple[float, float]] = {k: p for k, p in zip(keys, points) if k not in found}
    items = list(missing.items())
    for i in range(0, len(items), BATCH_SIZE):
        chunk = items[i : i + BATCH_SIZE]
        fetched = _fetch_batch([p for _, p in chunk])
        fresh = {k: f for (k, _), f in zip(chunk, fetched)}
        cache.set_many(fresh, settings.WEATHER_CACHE_SECONDS)
        found.update(fresh)

    return [found[k] for k in keys]
