import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _env_list(name: str, default: str) -> list[str]:
    return [v.strip() for v in os.getenv(name, default).split(",") if v.strip()]


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-insecure-key")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = _env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

if not DEBUG and SECRET_KEY == "dev-only-insecure-key":
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY when DJANGO_DEBUG=0.")

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "corsheaders",
    "routing",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# The app is stateless (no models), so no database is configured.
DATABASES: dict = {}

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
USE_TZ = True
TIME_ZONE = "UTC"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = _env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173")

# --- Weather routing configuration -------------------------------------------
OSRM_BASE_URL = os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org")
TRUCK_DURATION_FACTOR = float(os.getenv("TRUCK_DURATION_FACTOR", "1.15"))
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODER_URL = "https://nominatim.openstreetmap.org/search"
GEOCODER_USER_AGENT = os.getenv("GEOCODER_USER_AGENT", "spotter-weather-routing/1.0")
HTTP_TIMEOUT_SECONDS = 20
WEATHER_CACHE_SECONDS = 30 * 60
