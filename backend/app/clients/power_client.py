"""NASA POWER (power.larc.nasa.gov) daily point client.

Verified against the live API on 2026-11-14 with:
  GET https://power.larc.nasa.gov/api/temporal/daily/point
      ?parameters=T2M_MAX,T2M_MIN,T2M,PRECTOTCORR,GWETROOT,ALLSKY_SFC_SW_DWN,RH2M,WS2M
      &community=AG&longitude=73.08&latitude=31.42&start=20230101&end=20230110&format=JSON
-> HTTP 200 with all 8 parameters present (units: T2M*=C, PRECTOTCORR=mm/day,
   GWETROOT=unitless 0-1, ALLSKY_SFC_SW_DWN=MJ/m^2/day, RH2M=%, WS2M=m/s).
"""

from __future__ import annotations

import datetime as dt

from app.core.cache import cache_get, cache_key, cache_set
from app.core.config import get_settings
from app.core.http import UpstreamError, get_json

POWER_BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

PARAMETERS = [
    "T2M_MAX",
    "T2M_MIN",
    "T2M",
    "PRECTOTCORR",
    "GWETROOT",
    "ALLSKY_SFC_SW_DWN",
    "RH2M",
    "WS2M",
]

FILL_VALUE = -999.0


def latest_full_year() -> int:
    """NASA POWER data typically lags ~1-2 months behind real time, so the
    safest 'latest full year' is last calendar year."""
    return dt.datetime.utcnow().year - 1


async def fetch_power_daily(lat: float, lon: float, start_year: int | None = None, end_year: int | None = None) -> dict:
    """Fetch daily POWER data for every parameter, 2001 (or start_year) through
    end_year inclusive. Returns:

        {
          "ok": True,
          "start": "20010101", "end": "20241231",
          "series": {"T2M_MAX": {"20010101": 12.3, ...}, ...},  # fill values -> None
        }

    or {"ok": False, "error": "..."} if every retry attempt failed.
    """
    settings = get_settings()
    start_year = start_year or settings.power_start_year
    end_year = end_year or latest_full_year()

    key = cache_key("power", round(lat, 4), round(lon, 4), start_year, end_year)
    cached = cache_get(key)
    if cached is not None:
        cached["cache_hit"] = True
        return cached

    params = {
        "parameters": ",".join(PARAMETERS),
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": f"{start_year}0101",
        "end": f"{end_year}1231",
        "format": "JSON",
    }

    try:
        raw = await get_json(POWER_BASE_URL, params=params)
    except UpstreamError as exc:
        return {"ok": False, "error": str(exc), "cache_hit": False}

    try:
        param_block = raw["properties"]["parameter"]
    except (KeyError, TypeError):
        return {"ok": False, "error": "unexpected POWER response shape", "cache_hit": False}

    series: dict[str, dict[str, float | None]] = {}
    for p in PARAMETERS:
        raw_series = param_block.get(p, {})
        series[p] = {
            date: (None if value == FILL_VALUE else value) for date, value in raw_series.items()
        }

    result = {
        "ok": True,
        "start": f"{start_year}0101",
        "end": f"{end_year}1231",
        "series": series,
        "cache_hit": False,
    }
    cache_set(key, result)
    return result
