"""Route generation via OSRM, topped up to three distinct routes with via-point detours."""
from dataclasses import dataclass

import requests
from django.conf import settings

from .geo import LatLon, haversine_miles, offset_point, routes_overlap

METERS_PER_MILE = 1609.344
MAX_ROUTES = 3


class RoutingError(Exception):
    pass


@dataclass(frozen=True)
class RawRoute:
    path: list[LatLon]  # (lat, lon)
    distance_mi: float
    duration_s: float


def _request(waypoints: list[LatLon], alternatives: bool) -> list[RawRoute]:
    coords = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in waypoints)
    url = f"{settings.OSRM_BASE_URL}/route/v1/driving/{coords}"
    params = {
        "alternatives": "3" if alternatives else "false",
        "overview": "full",
        "geometries": "geojson",
        "steps": "false",
    }
    try:
        resp = requests.get(url, params=params, timeout=settings.HTTP_TIMEOUT_SECONDS)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RoutingError(f"Routing service unavailable: {exc}") from exc

    data = resp.json()
    if data.get("code") != "Ok":
        raise RoutingError(data.get("message") or f"No route found ({data.get('code')})")

    return [
        RawRoute(
            path=[(lat, lon) for lon, lat in r["geometry"]["coordinates"]],
            distance_mi=r["distance"] / METERS_PER_MILE,
            duration_s=r["duration"] * settings.TRUCK_DURATION_FACTOR,
        )
        for r in data["routes"]
    ]


def _add_if_distinct(routes: list[RawRoute], candidate: RawRoute) -> bool:
    if any(routes_overlap(candidate.path, existing.path) for existing in routes):
        return False
    routes.append(candidate)
    return True


def get_routes(origin: LatLon, destination: LatLon) -> list[RawRoute]:
    """Return up to three distinct routes, fastest first."""
    routes: list[RawRoute] = []
    for candidate in _request([origin, destination], alternatives=True):
        if len(routes) < MAX_ROUTES:
            _add_if_distinct(routes, candidate)

    if len(routes) < MAX_ROUTES:
        straight = haversine_miles(origin, destination)
        offset = min(max(straight * 0.12, 8.0), 60.0)
        for fraction, sign in ((0.5, 1), (0.5, -1), (0.35, 1), (0.65, -1), (0.35, -1), (0.65, 1)):
            if len(routes) >= MAX_ROUTES:
                break
            via = offset_point(origin, destination, fraction, sign * offset)
            try:
                detour = _request([origin, via, destination], alternatives=False)[0]
            except RoutingError:
                continue
            _add_if_distinct(routes, detour)

    routes.sort(key=lambda r: r.duration_s)
    return routes
