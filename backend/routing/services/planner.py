"""Orchestrates routes -> checkpoints -> weather -> risk -> recommendation."""
from dataclasses import dataclass
from datetime import datetime, timedelta

from .geo import LatLon, decimate, sample_checkpoints, segment_miles
from .osrm import RawRoute, get_routes
from .recommend import RouteStats, explain, rank_routes
from .risk import Risk, assess
from .weather import get_forecasts

ALLOWED_INTERVALS = (10, 25, 50)
HEATMAP_HOURS = 48  # slider covers 0..48 hours after departure
MAX_GEOMETRY_POINTS = 1500


@dataclass(frozen=True)
class PlanRequest:
    origin: LatLon
    destination: LatLon
    departure: datetime  # timezone-aware
    load_lb: float
    interval_miles: int


def _analyse_route(route_id: str, label: str, raw: RawRoute, req: PlanRequest) -> tuple[dict, RouteStats]:
    checkpoints = sample_checkpoints(raw.path, req.interval_miles)
    owned = segment_miles(checkpoints)
    forecasts = get_forecasts([(c.lat, c.lon) for c in checkpoints])
    total_mi = checkpoints[-1].mile or 1.0

    out_checkpoints = []
    miles_at = {level: 0.0 for level in Risk}
    weighted_risk = 0.0
    forecast_gaps = 0

    for i, (cp, fc, miles) in enumerate(zip(checkpoints, forecasts, owned)):
        eta = req.departure + timedelta(seconds=raw.duration_s * cp.mile / total_mi)
        weather, in_range = fc.at(eta)
        result = assess(weather, req.load_lb)
        forecast_gaps += not in_range

        miles_at[result.level] += miles
        weighted_risk += int(result.level) * miles

        hourly = [
            int(assess(fc.at(req.departure + timedelta(hours=h))[0], req.load_lb).level)
            for h in range(HEATMAP_HOURS + 1)
        ]
        out_checkpoints.append(
            {
                "index": i,
                "mile": round(cp.mile, 1),
                "lat": round(cp.lat, 5),
                "lon": round(cp.lon, 5),
                "eta": eta.isoformat(),
                "forecast_available": in_range,
                "weather": {
                    "wind_mph": round(weather.wind_mph, 1),
                    "rain_in_hr": round(weather.rain_in_hr, 2),
                    "snow_in_hr": round(weather.snow_in_hr, 2),
                },
                "risk": {"level": int(result.level), "label": result.level.label, "drivers": list(result.drivers)},
                "hourly_risk": hourly,
            }
        )

    avg_risk = weighted_risk / total_mi if total_mi else 0.0
    stats = RouteStats(
        route_id=route_id,
        no_travel_miles=miles_at[Risk.NO_TRAVEL],
        severe_miles=miles_at[Risk.SEVERE],
        high_miles=miles_at[Risk.HIGH],
        avg_risk=avg_risk,
        duration_s=raw.duration_s,
    )
    payload = {
        "id": route_id,
        "label": label,
        "distance_mi": round(raw.distance_mi, 1),
        "duration_s": round(raw.duration_s),
        "departure": req.departure.isoformat(),
        "arrival": (req.departure + timedelta(seconds=raw.duration_s)).isoformat(),
        "geometry": [[round(lat, 5), round(lon, 5)] for lat, lon in decimate(raw.path, MAX_GEOMETRY_POINTS)],
        "checkpoints": out_checkpoints,
        "summary": {
            "miles_by_risk": {r.label: round(miles_at[r], 1) for r in Risk},
            "no_travel_miles": round(stats.no_travel_miles, 1),
            "severe_miles": round(stats.severe_miles, 1),
            "high_miles": round(stats.high_miles, 1),
            "avg_risk": round(avg_risk, 2),
            "worst_risk": max((c["risk"]["level"] for c in out_checkpoints), default=0),
            "forecast_gaps": forecast_gaps,
            "checkpoint_count": len(out_checkpoints),
        },
    }
    return payload, stats


def plan(req: PlanRequest) -> dict:
    raw_routes = get_routes(req.origin, req.destination)
    labels = "ABC"
    analysed = [
        _analyse_route(f"route-{labels[i].lower()}", f"Route {labels[i]}", raw, req)
        for i, raw in enumerate(raw_routes)
    ]
    payloads = {p["id"]: p for p, _ in analysed}
    ranked = rank_routes([s for _, s in analysed])
    best = ranked[0]

    for rank, stats in enumerate(ranked, start=1):
        payloads[stats.route_id]["rank"] = rank
        payloads[stats.route_id]["recommended"] = rank == 1
    payloads[best.route_id]["reason"] = explain(best, ranked[1:])

    return {
        "recommended_route_id": best.route_id,
        "load_lb": req.load_lb,
        "interval_miles": req.interval_miles,
        "heatmap_hours": HEATMAP_HOURS,
        "routes": [payloads[p["id"]] for p, _ in analysed],
    }
