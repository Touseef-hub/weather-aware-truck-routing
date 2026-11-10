"""Weather risk classification (pure functions, no I/O).

Thresholds are lower-bound inclusive: a wind speed of exactly 25 mph is
Moderate, exactly 35 mph is High, and so on. Rain and snow top out with
"Severe" at the upper bound (1.00 in/hr, 3.0 in/hr) and become No Travel only
when strictly greater, matching the ">" in the brief.
"""
from dataclasses import dataclass
from enum import IntEnum


class Risk(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def label(self) -> str:
        return self.name.replace("_", " ").title()


# Lower bounds for Moderate, High, Severe.
WIND_BOUNDS = (25.0, 35.0, 45.0)
RAIN_BOUNDS = (0.10, 0.25, 0.50)
SNOW_BOUNDS = (0.5, 1.0, 2.0)

WIND_NO_TRAVEL_MPH = 55.0  # >= 55 mph
RAIN_NO_TRAVEL_IN_HR = 1.00  # > 1.00
SNOW_NO_TRAVEL_IN_HR = 3.0  # > 3.0

# Load rules
HEAVY_WIND_LOAD_LB = 30_000  # 45-54 mph and above this -> No Travel
VERY_HEAVY_WIND_LOAD_LB = 40_000  # 35-44 mph and above this -> Severe


@dataclass(frozen=True)
class Weather:
    wind_mph: float
    rain_in_hr: float
    snow_in_hr: float


@dataclass(frozen=True)
class RiskAssessment:
    level: Risk
    drivers: tuple[str, ...]  # which factors set the final level


def _level_from_bounds(value: float, bounds: tuple[float, float, float]) -> Risk:
    return Risk(sum(value >= b for b in bounds))


def classify_wind(mph: float) -> Risk:
    if mph >= WIND_NO_TRAVEL_MPH:
        return Risk.NO_TRAVEL
    return _level_from_bounds(mph, WIND_BOUNDS)


def classify_rain(in_hr: float) -> Risk:
    if in_hr > RAIN_NO_TRAVEL_IN_HR:
        return Risk.NO_TRAVEL
    return _level_from_bounds(in_hr, RAIN_BOUNDS)


def classify_snow(in_hr: float) -> Risk:
    if in_hr > SNOW_NO_TRAVEL_IN_HR:
        return Risk.NO_TRAVEL
    return _level_from_bounds(in_hr, SNOW_BOUNDS)


def apply_load_rules(wind_mph: float, load_lb: float, level: Risk) -> tuple[Risk, bool]:
    """Escalate `level` per the load rules. Returns (level, escalated_by_load)."""
    if wind_mph >= WIND_NO_TRAVEL_MPH:
        return Risk.NO_TRAVEL, False
    if wind_mph >= WIND_BOUNDS[2] and load_lb > HEAVY_WIND_LOAD_LB:
        escalated = Risk.NO_TRAVEL
    elif wind_mph >= WIND_BOUNDS[1] and load_lb > VERY_HEAVY_WIND_LOAD_LB:
        escalated = Risk.SEVERE
    else:
        return level, False
    return (escalated, True) if escalated > level else (level, False)


def assess(weather: Weather, load_lb: float) -> RiskAssessment:
    """Combine wind, rain and snow (worst one wins) and apply the load rules."""
    by_factor = {
        "wind": classify_wind(weather.wind_mph),
        "rain": classify_rain(weather.rain_in_hr),
        "snow": classify_snow(weather.snow_in_hr),
    }
    level = max(by_factor.values())
    drivers = [name for name, lvl in by_factor.items() if lvl == level and level > Risk.LOW]

    level, by_load = apply_load_rules(weather.wind_mph, load_lb, level)
    if by_load:
        drivers = ["wind", "load"]
    return RiskAssessment(level=level, drivers=tuple(drivers))
