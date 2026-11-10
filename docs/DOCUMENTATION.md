# Weather-Aware Truck Routing: Documentation

A React + TypeScript frontend and a Django backend that compare three driving routes by weather risk, load weight and travel time, and recommend the safest one.

This document is organised around the evaluation criteria in the brief, so each section says where to find the evidence.

| Criterion | Weight | Section |
|---|---|---|
| Routes, weather, risk and recommendation logic | 40% | [1. Logic](#1-routes-weather-risk-and-recommendation-logic) |
| UI, map and heatmap smoothness and performance | 40% | [2. UI and performance](#2-ui-map-and-heatmap-performance) |
| Code quality | 15% | [3. Code quality](#3-code-quality) |
| Documentation and walkthrough | 5% | This file, [README](../README.md), Loom walkthrough |

---

## 0. Quick start

```bash
# Backend: http://127.0.0.1:8000
cd backend
python -m venv .venv && .venv\Scripts\activate      # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py test        # 21 tests
python manage.py runserver

# Frontend: http://localhost:5173 (Vite proxies /api to the backend)
cd frontend
npm install
npm run dev
```

Configuration (all optional in development):

| Variable | Where | Purpose |
|---|---|---|
| `OSRM_BASE_URL` | backend | Routing server. Defaults to the public OSRM demo. |
| `TRUCK_DURATION_FACTOR` | backend | Multiplier on OSRM car durations. Default `1.15`. |
| `GEOCODER_USER_AGENT` | backend | Nominatim requires an identifying User-Agent. |
| `CORS_ALLOWED_ORIGINS` | backend | Frontend origin(s) in production. |
| `VITE_API_BASE_URL` | frontend | Backend URL in production. Empty in dev. |
| `VITE_TILE_URL` | frontend | Basemap tile URL. |

---

## 1. Routes, weather, risk and recommendation logic

### 1.1 Request flow

```
Origin / Destination / Departure / Load / Interval
        │
        ▼
POST /api/plan ──► osrm.get_routes()         up to 3 distinct routes
                        │
                        ▼  for each route
                   geo.sample_checkpoints()   every 10 / 25 / 50 mi, plus start and end
                        │
                        ▼
                   weather.get_forecasts()    Open-Meteo hourly, batched + cached
                        │
                        ▼
                   ETA per checkpoint         departure + duration × (mile / total miles)
                        │
                        ▼
                   risk.assess()              worst of wind/rain/snow, then load rules
                        │
                        ▼
                   recommend.rank_routes()    lexicographic ranking
```

Orchestration lives in `backend/routing/services/planner.py`. Every other module is either a pure function (`risk`, `recommend`, `geo`) or a thin wrapper around one external service (`osrm`, `weather`, `geocode`).

### 1.2 Generating three routes

`services/osrm.py` asks OSRM for alternatives first. OSRM often returns fewer than three, so the service tops up with detours: it routes via a waypoint pushed perpendicular to the straight line between origin and destination (at 35%, 50% and 65% of the way, on both sides). A candidate is discarded if at least 85% of its sampled points lie within 1.5 miles of a route we already have (`geo.routes_overlap`), so the three routes are genuinely different. Routes are returned fastest first.

### 1.3 Checkpoints and ETAs

- Checkpoints are placed at exact multiples of the chosen interval along the route geometry. The start and end are always included.
- ETA at a checkpoint is `departure + route_duration × (checkpoint_mile / total_miles)`. This assumes a constant average speed along each route.
- Route duration is OSRM's car duration multiplied by `TRUCK_DURATION_FACTOR` (1.15).

### 1.4 Weather

`services/weather.py` calls Open-Meteo for `wind_speed_10m`, `rain` and `snowfall`, requesting mph and inches directly so no conversion is needed.

- The checkpoint's weather is the forecast for the hour **nearest its ETA**.
- Locations are rounded to 2 decimal places (about 1 km). Points that round to the same cell share one cached forecast.
- Requests are batched 50 locations at a time. Responses are cached for 30 minutes.
- The forecast window is 7 days. A checkpoint whose ETA falls outside it uses the closest available hour and is marked `forecast_available: false`; the UI says so.

### 1.5 Risk classification

Implemented in `services/risk.py` as pure functions.

| Condition | Low | Moderate | High | Severe | No Travel |
|---|---|---|---|---|---|
| Wind | < 25 mph | 25 to < 35 | 35 to < 45 | 45 to < 55 | ≥ 55 |
| Rain | < 0.10 in/hr | 0.10 to < 0.25 | 0.25 to < 0.50 | 0.50 to 1.00 | > 1.00 |
| Snow | < 0.5 in/hr | 0.5 to < 1.0 | 1.0 to < 2.0 | 2.0 to 3.0 | > 3.0 |

Boundary decisions:

- Lower bounds are **inclusive**: exactly 25 mph is Moderate, exactly 35 mph is High.
- Rain and snow become No Travel only when strictly greater than 1.00 and 3.0, matching the `>` in the brief. So exactly 1.00 in/hr rain is Severe.

**Combining factors:** a checkpoint's level is the **worst** of wind, rain and snow. The result also records which factors set that level (`drivers`), which the map popup shows.

**Load rules** are applied after that and can only raise the level:

| Wind | Load | Result |
|---|---|---|
| ≥ 55 mph | any | No Travel |
| 45 to 54 mph | > 30,000 lb | No Travel |
| 35 to 44 mph | > 40,000 lb | Severe |

"Greater than" is strict: a 30,000 lb load at 50 mph stays Severe, and a 40,000 lb load at 40 mph stays High. Both cases have unit tests.

### 1.6 Recommendation

Implemented in `services/recommend.py`. Routes are sorted by this key, lowest first:

1. **No Travel miles**
2. **Severe miles**
3. **High miles**
4. **Average risk**, a distance-weighted mean of the 0 to 4 risk level
5. **Travel time**

The brief lists criteria 2 to 5. I rank No Travel miles first because a stretch that must not be driven is strictly worse than a Severe one; without this a route with 50 No Travel miles and 0 Severe miles could beat a merely Severe route. If you prefer the brief literally, remove the first element of the tuple in `ranking_key`.

The ranking is lexicographic, so a route with even slightly fewer Severe miles always wins, regardless of travel time. To stop floating point noise deciding ties, miles are compared to 0.1 and duration to whole minutes.

**Miles per risk level.** Each checkpoint owns half the gap to each neighbour (`geo.segment_miles`), so the miles across all levels add up to the route length.

The winning route carries a one-line `reason` naming the first criterion that separated it from the runner-up (for example "Fewer Severe miles").

### 1.7 API reference

`GET /api/health` returns `{"status": "ok"}`.

`GET /api/geocode?q=<text>` returns `{"results": [{"label", "lat", "lon"}]}`. Queries under 3 characters return an empty list.

`POST /api/plan`

```json
{
  "origin":      { "lat": 32.7767, "lon": -96.797, "label": "Dallas, TX" },
  "destination": { "lat": 39.7392, "lon": -104.9903, "label": "Denver, CO" },
  "departure": "2026-11-10T14:00:00Z",
  "load_lb": 42000,
  "interval_miles": 25
}
```

Validation errors return `400 {"error": "..."}`. Upstream failures (routing or weather service down) return `502`. `interval_miles` must be 10, 25 or 50; `load_lb` must be 0 to 150,000.

Response (abridged):

```json
{
  "recommended_route_id": "route-a",
  "heatmap_hours": 48,
  "routes": [{
    "id": "route-a", "label": "Route A",
    "distance_mi": 795.0, "duration_s": 59400,
    "arrival": "2026-11-11T06:30:00+00:00",
    "geometry": [[32.77, -96.79], "..."],
    "rank": 1, "recommended": true, "reason": "Fewer Severe miles",
    "summary": {
      "miles_by_risk": {"Low": 794.9, "Moderate": 0, "High": 0, "Severe": 0, "No Travel": 0},
      "severe_miles": 0, "high_miles": 0, "no_travel_miles": 0,
      "avg_risk": 0.0, "worst_risk": 0, "forecast_gaps": 0, "checkpoint_count": 33
    },
    "checkpoints": [{
      "index": 0, "mile": 0, "lat": 32.77, "lon": -96.79,
      "eta": "2026-11-10T14:00:00+00:00", "forecast_available": true,
      "weather": {"wind_mph": 8.1, "rain_in_hr": 0, "snow_in_hr": 0},
      "risk": {"level": 0, "label": "Low", "drivers": []},
      "hourly_risk": [0, 0, 0, "... 49 values, hour 0 to 48"]
    }]
  }]
}
```

### 1.8 Testing the logic

`python manage.py test` runs 21 tests with no network access:

- `test_risk.py`: every threshold boundary for wind, rain and snow; each load rule at, just below and just above its limit; load rules never lower a level; worst factor wins.
- `test_recommend.py`: each ranking criterion decides in order; No Travel ranks worse than Severe; the explanation names the right criterion; checkpoint spacing, endpoints and segment-mile sums.

---

## 2. UI, map and heatmap performance

### 2.1 What the user sees

- **Form:** origin and destination with autocomplete, departure date/time, load weight in pounds, and a 10 / 25 / 50 mile checkpoint selector.
- **Route cards:** one per route, with distance, duration, arrival time, a stacked bar of miles by risk level, Severe and High miles, average risk, a "Recommended" badge and the reason. No Travel miles and out-of-forecast checkpoints are flagged.
- **Map:** all three routes, with the selected one drawn thicker and on top. Click a route or card to select it. Checkpoints are coloured by risk level; clicking one shows mile, ETA, risk level and drivers, and wind, rain and snow values.
- **Heatmap:** a corridor heatmap with a 0 to 48 hour slider and legend. The slider is hours after departure and shows the forecast for that clock time at every checkpoint.

### 2.2 How the heatmap stays smooth

- **All 49 hours of risk come with the plan response** (`hourly_risk` on each checkpoint). Moving the slider never makes a network request.
- **One heat layer, created once.** `HeatLayer.tsx` builds the layer on mount and the slider only calls `setLatLngs` with new points. It draws on a single canvas, so scrubbing does not re-render React components or add DOM nodes.
- **Canvas rendering for markers.** The map uses Leaflet's `preferCanvas`, so hundreds of checkpoint markers (a 10 mile interval over a long route) are canvas shapes, not DOM elements.
- **Heat radius scales with the checkpoint interval**, so wide spacing does not leave visible gaps.

### 2.3 Other performance work

- **Weather batching and caching** on the backend: 50 locations per request, rounded and de-duplicated, cached for 30 minutes. A second search over the same corridor is served from memory.
- **Geometry decimation:** route polylines are thinned to at most 1,500 points before sending.
- **Debounced autocomplete** (400 ms) with request cancellation, so typing does not flood the geocoder.
- **Stale requests are aborted.** Submitting a new plan cancels the one in flight, and a late response can never overwrite a newer one.
- The production bundle is about 97 kB gzipped.

### 2.4 Front-end structure

```
frontend/src/
  App.tsx                 state: input, result, selection, hour, loading, error
  types.ts                API types
  risk.ts, format.ts      colours/labels, date and duration formatting
  services/api.ts         fetch wrapper (the only place that talks to the backend)
  components/
    PlanForm.tsx          inputs + validation
    PlaceInput.tsx        autocomplete
    RouteList.tsx         route cards + risk bar
    MapView.tsx           map, routes, checkpoints, popups
    HeatLayer.tsx         heat layer lifecycle
    HeatmapControls.tsx   toggle, slider, legend
```

---

## 3. Code quality

- **Pure core, thin edges.** Risk and ranking are pure functions with no I/O, which is why they are fully unit tested. Network access is isolated in `osrm.py`, `weather.py` and `geocode.py`.
- **One orchestrator.** `planner.py` is the only module that wires the pieces together; views only parse, validate and serialise.
- **Validation at the boundary.** `views.py` rejects bad coordinates, load weights, intervals and timestamps with a clear 400. Missing timezones on `departure` are treated as UTC.
- **Typed frontend.** TypeScript in strict mode with `noUnusedLocals` and `noUnusedParameters`. `npm run typecheck` is clean.
- **Named constants over magic numbers.** Thresholds, bounds and limits are defined once at the top of their module.
- **No secrets in the repo.** Configuration is read from environment variables; `.env.example` files document them.

---

## 4. Assumptions and limitations

- **ETAs assume constant speed** along each route. There is no traffic, rest-stop or hours-of-service modelling.
- **OSRM uses a car profile.** Truck restrictions (height, weight, hazmat) are not applied; durations are only scaled by 1.15.
- **Wind is sustained 10 m speed, not gusts.** Gusts would be a stricter and arguably more realistic input.
- **Snow** uses Open-Meteo's snowfall depth per hour directly as in/hr.
- **Time zones:** times are shown in the viewer's browser time zone, not each checkpoint's local time.
- **Forecast window** is 7 days; the heatmap covers the first 48 hours after departure.
- **Third-party limits:** the public OSRM demo and OSM tile servers are for light use, and Open-Meteo's free tier is for non-commercial use. Set `OSRM_BASE_URL` and `VITE_TILE_URL` for production.
- **No persistence.** The app is stateless: no database, no saved trips, no accounts.

---

## 5. Deliverables checklist

- [ ] GitHub repository: _add link_
- [ ] Hosted application: _add link_. Steps in [DEPLOYMENT.md](DEPLOYMENT.md) (Render for the API, Vercel for the frontend)
- [ ] Loom walkthrough (5 to 10 minutes): _add link_
