import json
import logging
from datetime import datetime, timezone

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .services.geocode import GeocodeError, search_places
from .services.osrm import RoutingError
from .services.planner import ALLOWED_INTERVALS, PlanRequest, plan
from .services.weather import WeatherError

logger = logging.getLogger(__name__)

MAX_LOAD_LB = 150_000


class ValidationError(Exception):
    pass


def _error(message: str, status: int) -> JsonResponse:
    return JsonResponse({"error": message}, status=status)


def _parse_point(data: dict, field: str) -> tuple[float, float]:
    point = data.get(field) or {}
    try:
        lat, lon = float(point["lat"]), float(point["lon"])
    except (KeyError, TypeError, ValueError):
        raise ValidationError(f"'{field}' must include numeric lat and lon.")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValidationError(f"'{field}' coordinates are out of range.")
    return lat, lon


def _parse_plan_request(body: bytes) -> PlanRequest:
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        raise ValidationError("Request body must be valid JSON.")

    try:
        departure = datetime.fromisoformat(str(data.get("departure")).replace("Z", "+00:00"))
    except ValueError:
        raise ValidationError("'departure' must be an ISO 8601 date/time.")
    if departure.tzinfo is None:
        departure = departure.replace(tzinfo=timezone.utc)

    try:
        load_lb = float(data.get("load_lb"))
    except (TypeError, ValueError):
        raise ValidationError("'load_lb' must be a number.")
    if not 0 <= load_lb <= MAX_LOAD_LB:
        raise ValidationError(f"'load_lb' must be between 0 and {MAX_LOAD_LB}.")

    interval = int(data.get("interval_miles") or 25)
    if interval not in ALLOWED_INTERVALS:
        raise ValidationError(f"'interval_miles' must be one of {list(ALLOWED_INTERVALS)}.")

    return PlanRequest(
        origin=_parse_point(data, "origin"),
        destination=_parse_point(data, "destination"),
        departure=departure,
        load_lb=load_lb,
        interval_miles=interval,
    )


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})


@require_GET
def geocode(request):
    query = request.GET.get("q", "").strip()
    if len(query) < 3:
        return JsonResponse({"results": []})
    try:
        return JsonResponse({"results": search_places(query)})
    except GeocodeError as exc:
        logger.warning("geocode failed: %s", exc)
        return _error(str(exc), 502)


@require_POST
def plan_route(request):
    try:
        plan_request = _parse_plan_request(request.body)
        return JsonResponse(plan(plan_request))
    except ValidationError as exc:
        return _error(str(exc), 400)
    except (RoutingError, WeatherError) as exc:
        logger.warning("plan failed: %s", exc)
        return _error(str(exc), 502)
