"""
signals/geolocation.py

Reverse geocoding for GPS coordinates that were actually extracted from an
image's embedded EXIF GPS metadata. This module never invents or infers a
location from anything other than the (latitude, longitude) it is given —
callers are responsible for only calling it with real embedded GPS data.

Uses OpenStreetMap's Nominatim reverse-geocoding service (free, no API key,
appropriate for a low-volume prototype), respecting its usage policy: an
identifying User-Agent, a timeout, and at most ~1 request/second. Results
are cached on disk so repeated analysis of the same coordinates doesn't
repeatedly hit the service.

Public entry point: reverse_geocode(latitude, longitude, timeout=5.0)
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = PROJECT_ROOT / "data" / "cache" / "geocode_cache.json"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"

# Identifies this tool to Nominatim, per its usage policy. No personal
# contact details are sent — just a project identifier and the public repo.
USER_AGENT = (
    "VeritasLens-ForensicPrototype/0.1 "
    "(+https://github.com/OjasPurohit/DeepEntra-Build-Fest-Masons-CYB-03)"
)

MIN_REQUEST_INTERVAL_SECONDS = 1.1  # Nominatim policy: max ~1 req/sec

_last_request_time = 0.0
_cache: Optional[dict] = None


def _load_cache() -> dict:
    global _cache
    if _cache is not None:
        return _cache

    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            _cache = json.load(f)
    except Exception:
        _cache = {}

    return _cache


def _save_cache() -> None:
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(_cache, f, indent=2)
    except Exception:
        pass  # caching is a convenience; never fail the caller over it


def _cache_key(latitude: float, longitude: float) -> str:
    # Round to ~1m precision -- enough to reuse a lookup for the same spot
    # without conflating genuinely different locations.
    return f"{round(latitude, 5)},{round(longitude, 5)}"


def _empty_result(latitude, longitude, error: Optional[str] = None) -> dict:
    return {
        "available": False,
        "latitude": latitude,
        "longitude": longitude,
        "display_name": None,
        "city": None,
        "state": None,
        "country": None,
        "postcode": None,
        "road": None,
        "house_number": None,
        "error": error,
    }


def reverse_geocode(latitude: float, longitude: float, timeout: float = 5.0) -> dict:
    """
    Reverse-geocode real GPS coordinates into an approximate place
    description. Never raises: any network/parsing failure returns the
    coordinates with every location field set to None/unavailable rather
    than a fabricated place name.
    """

    global _last_request_time

    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError) as exc:
        return _empty_result(latitude, longitude, error=f"Invalid coordinates: {exc}")

    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return _empty_result(latitude, longitude, error="Coordinates out of valid range")

    cache = _load_cache()
    key = _cache_key(latitude, longitude)
    if key in cache:
        return cache[key]

    try:
        import requests

        elapsed = time.monotonic() - _last_request_time
        if elapsed < MIN_REQUEST_INTERVAL_SECONDS:
            time.sleep(MIN_REQUEST_INTERVAL_SECONDS - elapsed)

        response = requests.get(
            NOMINATIM_URL,
            params={
                "format": "jsonv2",
                "lat": latitude,
                "lon": longitude,
                "zoom": 18,
                "addressdetails": 1,
            },
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
        )
        _last_request_time = time.monotonic()
        response.raise_for_status()
        data = response.json()

        address = data.get("address", {}) or {}
        city = address.get("city") or address.get("town") or address.get("village") or address.get("suburb")

        result = {
            "available": True,
            "latitude": latitude,
            "longitude": longitude,
            "display_name": data.get("display_name"),
            "city": city,
            "state": address.get("state"),
            "country": address.get("country"),
            "postcode": address.get("postcode"),
            "road": address.get("road"),
            "house_number": address.get("house_number"),
            "error": None,
        }

        cache[key] = result
        _save_cache()
        return result

    except Exception as exc:
        # Never fail the caller over a network/service problem; keep the
        # real coordinates, mark the place-name fields as unavailable.
        return _empty_result(latitude, longitude, error=f"{type(exc).__name__}: {exc}")
