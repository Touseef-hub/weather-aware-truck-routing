# Deployment (free tier)

**Plan:** the Django API on **Render** (free web service) and the React app on **Vercel** (free Hobby plan). Both deploy from one GitHub repository. Free-tier limits change, so check the current pricing pages if something below doesn't match what you see.

```
Browser ──► Vercel (static React build) ──► Render (Django + gunicorn) ──► OSRM / Open-Meteo / Nominatim
```

The frontend calls the backend directly. In development Vite proxies `/api`; in production the frontend needs the backend's URL at **build time** (`VITE_API_BASE_URL`).

## 0. What I already verified locally

- `python manage.py test` passes (21 tests).
- With `DJANGO_DEBUG=0` the app refuses to start without `DJANGO_SECRET_KEY`.
- `collectstatic` succeeds, and `npm run build` (the Vercel build command) succeeds.
- Not run locally: gunicorn (it does not run on Windows) and the actual hosted services. Expect to fix small things on the first deploy.

## 1. Push to GitHub

This folder is not a git repository yet.

```bash
cd spotter-task
git init
git add .
git status        # confirm .venv, node_modules, .env and dist are NOT listed
git commit -m "Weather-aware truck routing"
git branch -M main
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

`.gitignore` already excludes `.venv/`, `node_modules/`, `dist/` and `.env`. The PDF of the brief is in the folder; remove it from the commit if you'd rather not publish it.

## 2. Deploy the backend on Render

**Option A: Blueprint (recommended).** `render.yaml` at the repo root defines the service.

1. Render dashboard, **New**, **Blueprint**, connect the GitHub repo.
2. Render reads `render.yaml`. It will prompt for the two values marked `sync: false`:
   - `CORS_ALLOWED_ORIGINS`: leave blank for now; you'll set it after step 3.
   - `GEOCODER_USER_AGENT`: for example `truck-routing/1.0 (contact: you@example.com)`. Nominatim's policy requires an identifying value.
3. Apply. Wait for the first deploy to finish.

**Option B: manual web service.**

| Setting | Value |
|---|---|
| Runtime | Python 3 |
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt && python manage.py collectstatic --noinput` |
| Start Command | `gunicorn config.wsgi:application --workers 2 --timeout 120 --bind 0.0.0.0:$PORT` |
| Health Check Path | `/api/health` |
| Instance type | Free |

Environment variables:

| Key | Value |
|---|---|
| `PYTHON_VERSION` | `3.12.4` |
| `DJANGO_SECRET_KEY` | a long random string (Render can generate one) |
| `DJANGO_DEBUG` | `0` |
| `DJANGO_ALLOWED_HOSTS` | `.onrender.com` |
| `CORS_ALLOWED_ORIGINS` | your Vercel URL, set after step 3 |
| `GEOCODER_USER_AGENT` | as above |

`--timeout 120` matters: planning a long route makes several routing and weather calls, which can exceed gunicorn's default 30 seconds.

**Check it:** open `https://<your-service>.onrender.com/api/health`. You should see `{"status": "ok"}`.

## 3. Deploy the frontend on Vercel

1. Vercel dashboard, **Add New**, **Project**, import the same GitHub repo.
2. Set:

| Setting | Value |
|---|---|
| Framework Preset | Vite |
| Root Directory | `frontend` |
| Build Command | `npm run build` |
| Output Directory | `dist` |

3. Add environment variable `VITE_API_BASE_URL` = `https://<your-service>.onrender.com` (no trailing slash, no `/api`).
4. Deploy and note the URL, for example `https://truck-routing.vercel.app`.

`VITE_*` variables are baked in at build time, so **changing the value requires a redeploy.**

## 4. Connect them (CORS)

Back in Render, set `CORS_ALLOWED_ORIGINS` to the exact Vercel URL, with `https://` and no trailing slash, then let the service redeploy.

```
CORS_ALLOWED_ORIGINS=https://truck-routing.vercel.app
```

Vercel preview deployments get different URLs and will be blocked by CORS; only the production URL works unless you add the preview URLs (comma separated).

## 5. Smoke test on the hosted app

1. Open the Vercel URL. The map should load.
2. Type a city in Origin: suggestions should appear (tests the geocoder through the backend).
3. Plan Dallas, TX to Denver, CO. You should get three routes within roughly 10 to 30 seconds on the free tier.
4. Toggle the heatmap and drag the slider.
5. Browser dev tools, Network tab: requests go to `onrender.com` and return 200, with no CORS errors in the console.

## 6. Free-tier behaviour to know about

- **Cold starts.** A free Render service sleeps after a period of inactivity, and the first request afterwards can take around a minute. **Open `/api/health` a minute or two before recording the Loom or sharing the link**, and mention it in the README so a reviewer isn't surprised by a slow first request. An uptime monitor pinging `/api/health` every few minutes can keep it warm if you want.
- **Cache is per process and is lost on restart.** Django's in-memory cache is used (two gunicorn workers each have their own). That only costs a few extra weather calls; it does not affect correctness.
- **Memory.** Free instances have limited RAM. Plans at the 10 mile interval over very long routes build the largest responses; if the service is killed, use the 25 or 50 mile interval, or lower gunicorn to `--workers 1`.
- **Third-party services.** The public OSRM demo, Nominatim, Open-Meteo's free tier and the public OSM tile server are for light use. That is fine for a demonstration; for real traffic, self-host or pay for providers (`OSRM_BASE_URL`, `VITE_TILE_URL`).

## 7. Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| Page loads, searches fail with "Failed to fetch" and a CORS error in the console | `CORS_ALLOWED_ORIGINS` is missing, has a trailing slash, or doesn't match the Vercel URL exactly. |
| Requests go to the Vercel domain and return 404 | `VITE_API_BASE_URL` was not set at build time. Set it and redeploy. |
| Backend returns 400 `DisallowedHost` | `DJANGO_ALLOWED_HOSTS` does not cover the Render hostname. `.onrender.com` covers all subdomains. |
| Backend fails to start with `Set DJANGO_SECRET_KEY` | `DJANGO_DEBUG=0` but no secret key set. |
| Plan returns 502 "Routing service unavailable" | The public OSRM demo is busy. Retry; consider a different `OSRM_BASE_URL`. |
| Plan returns 502 "Weather service unavailable" | Open-Meteo rate limit or outage. Retry shortly. |
| First request after idle takes about a minute | Free-tier cold start. See section 6. |
| Worker timeout in the Render logs | A very long route took over 120 s. Raise `--timeout`, or use a wider checkpoint interval. |

## 8. Alternative: everything on Render

If you'd rather keep one platform, create a Render **Static Site** for the frontend: Root Directory `frontend`, Build Command `npm install && npm run build`, Publish Directory `dist`, with the same `VITE_API_BASE_URL` environment variable. Steps 4 to 7 are the same, with the static site's URL used for CORS.

## 9. Security notes

`manage.py check --deploy` reports warnings about CSRF middleware, clickjacking headers, HSTS and SSL redirect. They are intentional here: the API is stateless JSON with no cookies, sessions or login, so there is no session to forge, and Render terminates HTTPS in front of the app. If you add authentication later, enable `CsrfViewMiddleware`, `XFrameOptionsMiddleware` and the `SECURE_*` settings.
