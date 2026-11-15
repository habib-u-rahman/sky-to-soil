"""MODIS MOD13Q1 (250 m, 16-day) NDVI client via the ORNL DAAC MODIS web
service: https://modis.ornl.gov/rst/api/v1/

Verified against the live API on 2026-11-14:
  GET /MOD13Q1/bands
    -> confirms band names "250m_16_days_NDVI" (scale_factor 0.0001,
       fill_value -3000) and "250m_16_days_pixel_reliability"
       (rank 0-3: 0=good, 1=marginal, 2=snow/ice, 3=cloudy).
  GET /MOD13Q1/dates?latitude=31.42&longitude=73.08
    -> returns the full list of available 16-day composite dates back to 2000.
  GET /MOD13Q1/subset?latitude=31.42&longitude=73.08&band=250m_16_days_NDVI
      &startDate=A2023001&endDate=A2023017&kmAboveBelow=0&kmLeftRight=0
    -> returns per-composite single-pixel values; startDate/endDate do not
       need to exactly match an available composite date, the service
       returns whatever composites fall inside the requested window.

IMPORTANT, also verified live: the subset endpoint caps how much time you
can request in one call. A 2-year window
(startDate=A2022001&endDate=A2023365) returned HTTP 400:
  "Subset time period A2022001 to A2023365 exceeds maximum subset tiles
   support of 10."
10 composites x 16 days = 160 days max per request. fetch_ndvi_timeseries
below chunks any longer request into <=150-day windows and fetches them
concurrently.

Note: this sandbox's curl required --ssl-no-revoke (Windows schannel OCSP
check blocked by the network); httpx uses its own TLS stack and was not
affected in testing.
"""

from __future__ import annotations

import asyncio
import datetime as dt

from app.core.cache import cache_get, cache_key, cache_set
from app.core.http import UpstreamError, get_json

ORNL_BASE_URL = "https://modis.ornl.gov/rst/api/v1/MOD13Q1"

NDVI_BAND = "250m_16_days_NDVI"
QUALITY_BAND = "250m_16_days_pixel_reliability"
NDVI_SCALE = 0.0001
NDVI_FILL = -3000

QUALITY_LABELS = {0: "good", 1: "marginal", 2: "snow_ice", 3: "cloudy"}
USABLE_QUALITY_CODES = {0, 1}

# The ORNL subset endpoint rejects windows spanning more than 10 composites
# (160 days); chunk requests to stay safely under that.
MAX_CHUNK_DAYS = 150

# Firing every chunk's NDVI+QA band pair fully concurrently works fine for
# a 1-2 year window (a handful of chunks), but a multi-year (2018-latest)
# fetch is ~20 chunks x 2 bands = 40 simultaneous requests -- verified live
# that this reliably trips ORNL's rate limiting (bursts of 503 Service
# Unavailable). Capping in-flight chunks keeps the chunking's benefit
# (still far faster than one-at-a-time) without the burst.
MAX_CONCURRENT_CHUNKS = 4


def _to_modis_date(calendar_date: str) -> str:
    """'2023-01-17' -> 'A2023017'."""
    d = dt.date.fromisoformat(calendar_date)
    return f"A{d.year}{d.timetuple().tm_yday:03d}"


def _chunk_date_range(start_date: str, end_date: str, max_days: int = MAX_CHUNK_DAYS) -> list[tuple[str, str]]:
    start = dt.date.fromisoformat(start_date)
    end = dt.date.fromisoformat(end_date)
    chunks = []
    cursor = start
    while cursor <= end:
        chunk_end = min(cursor + dt.timedelta(days=max_days), end)
        chunks.append((cursor.isoformat(), chunk_end.isoformat()))
        cursor = chunk_end + dt.timedelta(days=1)
    return chunks


async def _fetch_band(lat: float, lon: float, band: str, start_modis: str, end_modis: str) -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "band": band,
        "startDate": start_modis,
        "endDate": end_modis,
        "kmAboveBelow": 0,
        "kmLeftRight": 0,
    }
    url = f"{ORNL_BASE_URL}/subset"
    return await get_json(url, params=params)


async def fetch_ndvi_timeseries(lat: float, lon: float, start_date: str, end_date: str) -> dict:
    """Fetch quality-filtered NDVI time series between start_date and end_date
    (ISO 'YYYY-MM-DD' strings).

    Returns:
        {"ok": True, "points": [{"modis_date", "calendar_date", "ndvi",
                                   "quality_code", "quality_label", "usable"}, ...],
         "cache_hit": False}
      or {"ok": False, "error": "..."}
    """
    key = cache_key("modis_ndvi", round(lat, 4), round(lon, 4), start_date, end_date)
    cached = cache_get(key)
    if cached is not None:
        cached["cache_hit"] = True
        return cached

    chunks = _chunk_date_range(start_date, end_date)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_CHUNKS)

    async def fetch_chunk(chunk_start: str, chunk_end: str):
        start_modis = _to_modis_date(chunk_start)
        end_modis = _to_modis_date(chunk_end)
        async with semaphore:
            # Fetch the NDVI and quality bands concurrently -- ORNL's web
            # service can take tens of seconds per band request on this
            # network, and the two bands are independent, so doing them
            # sequentially roughly doubles the wait for no reason. The
            # semaphore above caps how many CHUNKS (pairs of these) run at
            # once across the whole fetch.
            try:
                return await asyncio.gather(
                    _fetch_band(lat, lon, NDVI_BAND, start_modis, end_modis),
                    _fetch_band(lat, lon, QUALITY_BAND, start_modis, end_modis),
                )
            except UpstreamError:
                # A single chunk failing (e.g. one transient 503) shouldn't
                # zero out a multi-year fetch spanning ~20 chunks -- skip
                # just this window and keep the rest.
                return None

    chunk_results = [r for r in await asyncio.gather(*(fetch_chunk(s, e) for s, e in chunks)) if r is not None]
    if not chunk_results:
        return {"ok": False, "error": "every chunk in this date range failed", "cache_hit": False}

    points_by_date: dict[str, dict] = {}
    for ndvi_raw, qa_raw in chunk_results:
        qa_by_date = {item["modis_date"]: item["data"][0] for item in qa_raw.get("subset", [])}
        for item in ndvi_raw.get("subset", []):
            modis_date = item["modis_date"]
            raw_value = item["data"][0]
            quality_code = qa_by_date.get(modis_date)
            ndvi = None if raw_value == NDVI_FILL else round(raw_value * NDVI_SCALE, 4)
            usable = quality_code in USABLE_QUALITY_CODES if quality_code is not None else False
            points_by_date[modis_date] = {
                "modis_date": modis_date,
                "calendar_date": item["calendar_date"],
                "ndvi": ndvi,
                "quality_code": quality_code,
                "quality_label": QUALITY_LABELS.get(quality_code, "unknown") if quality_code is not None else None,
                "usable": bool(usable and ndvi is not None),
            }

    points = sorted(points_by_date.values(), key=lambda p: p["calendar_date"])

    result = {"ok": True, "points": points, "cache_hit": False}
    cache_set(key, result)
    return result
