"""Place search via Nominatim (OpenStreetMap)."""
import requests
from django.conf import settings
from django.core.cache import cache


class GeocodeError(Exception):
    pass


def search_places(query: str, limit: int = 5) -> list[dict]:
    key = f"geo:{query.strip().lower()}:{limit}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    try:
        resp = requests.get(
            settings.GEOCODER_URL,
            params={"q": query, "format": "jsonv2", "limit": limit, "countrycodes": "us,ca,mx"},
            headers={"User-Agent": settings.GEOCODER_USER_AGENT},
            timeout=settings.HTTP_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise GeocodeError(f"Geocoding service unavailable: {exc}") from exc

    places = [
        {"label": item["display_name"], "lat": float(item["lat"]), "lon": float(item["lon"])}
        for item in resp.json()
    ]
    cache.set(key, places, 24 * 3600)
    return places
