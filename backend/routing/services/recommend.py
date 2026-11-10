"""Route ranking (pure functions)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class RouteStats:
    route_id: str
    no_travel_miles: float
    severe_miles: float
    high_miles: float
    avg_risk: float  # distance-weighted mean of the 0-4 risk level
    duration_s: float


def ranking_key(s: RouteStats) -> tuple[float, float, float, float, float]:
    """Lower is better.

    Order follows the brief: fewest Severe miles, then fewest High miles, then
    lowest average risk, then shortest travel time. No Travel miles are ranked
    first because a No Travel stretch is strictly worse than a Severe one.
    Values are rounded so float noise cannot decide a tie.
    """
    return (
        round(s.no_travel_miles, 1),
        round(s.severe_miles, 1),
        round(s.high_miles, 1),
        round(s.avg_risk, 3),
        round(s.duration_s / 60),  # whole minutes
    )


def rank_routes(stats: list[RouteStats]) -> list[RouteStats]:
    return sorted(stats, key=ranking_key)


def explain(best: RouteStats, others: list[RouteStats]) -> str:
    """One-line reason the best route won, naming the first criterion that separated it."""
    if not others:
        return "Only one route was available."
    runner_up = min(others, key=ranking_key)
    labels = ("No Travel miles", "Severe miles", "High miles", "average risk", "travel time")
    for label, a, b in zip(labels, ranking_key(best), ranking_key(runner_up)):
        if a < b:
            if label == "travel time":
                return "Weather risk is equivalent to the alternatives; this is the fastest."
            return f"Fewer {label}" if "miles" in label else f"Lower {label}"
    return "Tied with the alternatives on every criterion; this is the fastest."
