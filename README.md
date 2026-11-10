# Weather-Aware Truck Routing

React + TypeScript frontend and Django backend that compares three driving routes by weather risk, load weight and travel time, and recommends the safest one.

## Run locally

```bash
# Backend (http://127.0.0.1:8000)
cd backend
python -m venv .venv && .venv/Scripts/activate      # source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env
python manage.py test
python manage.py runserver

# Frontend (http://localhost:5173, proxies /api to the backend)
cd frontend
npm install
npm run dev
```

## Docs

- [docs/DOCUMENTATION.md](docs/DOCUMENTATION.md): logic, API, performance, assumptions
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md): free hosting on Render (API) and Vercel (frontend)

## How it works

| Step | Where | Notes |
|---|---|---|
| Geocoding | `services/geocode.py` | Nominatim (OSM), cached 24h |
| 3 routes | `services/osrm.py` | OSRM alternatives, topped up with via-point detours; near-duplicate routes are discarded |
| Checkpoints | `services/geo.py` | Every 10/25/50 mi along the geometry, plus start and end |
| ETA | `services/planner.py` | Departure + route duration × (checkpoint mile / total miles) |
| Weather | `services/weather.py` | Open-Meteo hourly forecast, batched and cached; value taken for the hour nearest the ETA |
| Risk | `services/risk.py` | Pure functions: worst of wind/rain/snow, then load rules |
| Recommendation | `services/recommend.py` | Pure functions |

API: `GET /api/geocode?q=`, `POST /api/plan`, `GET /api/health`.

## Decisions and assumptions

- **Boundaries** are lower-bound inclusive (25 mph is Moderate, 35 is High, 45 is Severe, 55 is No Travel). Rain above 1.00 in/hr and snow above 3.0 in/hr are No Travel.
- **Combining factors:** the checkpoint's level is the worst of wind, rain and snow. Load rules can only raise it, never lower it.
- **Miles per risk level:** each checkpoint owns half the gap to its neighbours, so the miles add up to the route length.
- **Ranking:** No Travel miles, then Severe miles, then High miles, then distance-weighted average risk, then duration. No Travel is ranked first because a No Travel stretch is worse than a Severe one. Durations are compared in whole minutes and miles to 0.1 so rounding noise can't decide a tie.
- **Snow:** Open-Meteo reports snowfall depth per hour, which is used directly as in/hr.
- **Wind:** sustained 10 m wind speed, not gusts.
- **Heatmap:** the slider is hours after departure (0–48). It shows the forecast for that clock time at every checkpoint, so it answers "what does the corridor look like at hour N". The route's own risk uses each checkpoint's ETA.
- **Forecast window:** 7 days. Checkpoints beyond it use the last available hour and are flagged in the UI.
- **Duration:** OSRM uses a car profile, so durations are multiplied by `TRUCK_DURATION_FACTOR` (1.15). It knows nothing about truck restrictions, hours-of-service or weigh stations.

## Known limitations

- The public OSRM demo and OSM tile servers are for light use. Self-host or swap providers for production (`OSRM_BASE_URL`, `VITE_TILE_URL`).
- Open-Meteo's free tier is for non-commercial use.
- ETAs are shown in the viewer's browser time zone, not the time zone of each checkpoint.
