"""Geometry helpers: distances, checkpoint sampling, route overlap."""
import math
from dataclasses import dataclass

EARTH_RADIUS_MI = 3958.8

LatLon = tuple[float, float]


@dataclass(frozen=True)
class Checkpoint:
    mile: float
    lat: float
    lon: float


def haversine_miles(a: LatLon, b: LatLon) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_MI * math.asin(math.sqrt(h))


def cumulative_miles(path: list[LatLon]) -> list[float]:
    total = 0.0
    out = [0.0]
    for prev, cur in zip(path, path[1:]):
        total += haversine_miles(prev, cur)
        out.append(total)
    return out


def sample_checkpoints(path: list[LatLon], interval_miles: float) -> list[Checkpoint]:
    """Points every `interval_miles` along the path, always including start and end."""
    cum = cumulative_miles(path)
    total = cum[-1]
    targets = [i * interval_miles for i in range(int(total // interval_miles) + 1)]
    if total - targets[-1] > 1e-6:
        targets.append(total)

    checkpoints: list[Checkpoint] = []
    seg = 0
    for target in targets:
        while seg < len(path) - 2 and cum[seg + 1] < target:
            seg += 1
        span = cum[seg + 1] - cum[seg]
        t = 0.0 if span == 0 else min(max((target - cum[seg]) / span, 0.0), 1.0)
        lat = path[seg][0] + (path[seg + 1][0] - path[seg][0]) * t
        lon = path[seg][1] + (path[seg + 1][1] - path[seg][1]) * t
        checkpoints.append(Checkpoint(mile=target, lat=lat, lon=lon))
    return checkpoints


def segment_miles(checkpoints: list[Checkpoint]) -> list[float]:
    """Miles of road each checkpoint 'owns': half the gap on either side."""
    n = len(checkpoints)
    if n == 1:
        return [0.0]
    owned = []
    for i, cp in enumerate(checkpoints):
        before = (cp.mile - checkpoints[i - 1].mile) / 2 if i > 0 else 0.0
        after = (checkpoints[i + 1].mile - cp.mile) / 2 if i < n - 1 else 0.0
        owned.append(before + after)
    return owned


def decimate(path: list[LatLon], max_points: int) -> list[LatLon]:
    if len(path) <= max_points:
        return path
    step = len(path) / max_points
    thinned = [path[int(i * step)] for i in range(max_points)]
    thinned.append(path[-1])
    return thinned


def routes_overlap(a: list[LatLon], b: list[LatLon], tolerance_miles: float = 1.5, share: float = 0.85) -> bool:
    """True if at least `share` of sampled points on `a` lie within tolerance of `b`."""
    samples = decimate(a, 40)
    probe = decimate(b, 400)
    near = sum(1 for p in samples if min(haversine_miles(p, q) for q in probe) <= tolerance_miles)
    return near / len(samples) >= share


def offset_point(origin: LatLon, destination: LatLon, fraction: float, offset_miles: float) -> LatLon:
    """Point `fraction` of the way along origin->destination, pushed perpendicular by offset_miles."""
    lat = origin[0] + (destination[0] - origin[0]) * fraction
    lon = origin[1] + (destination[1] - origin[1]) * fraction
    dlat = destination[0] - origin[0]
    dlon = (destination[1] - origin[1]) * math.cos(math.radians(lat))
    norm = math.hypot(dlat, dlon) or 1.0
    # Unit vector rotated 90 degrees.
    nlat, nlon = -dlon / norm, dlat / norm
    deg = offset_miles / 69.0
    return lat + nlat * deg, lon + nlon * deg / max(math.cos(math.radians(lat)), 0.01)
