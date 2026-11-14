"""Service layer: combines clients + science modules into the shapes the
routers return (everything except the `location` field, which routers add)."""

from __future__ import annotations

import datetime as dt

from app.clients.modis_client import fetch_ndvi_timeseries
from app.clients.power_client import fetch_power_daily, latest_full_year
from app.clients.soilgrids_client import fetch_soil_profile
from app.core.sources import source_meta
from app.data.crop_repo import load_crops
from app.science.climate import DEFAULT_SEASONS, analyze_climate_shift
from app.science.climatology import build_doy_climatology
from app.science.rotation_engine import score_all_rotations, stress_test_rotations

def _season_config_to_dict(season_config) -> dict:
    if season_config is None:
        return DEFAULT_SEASONS
    return {
        "kharif": {"start_month": season_config.kharif.start_month, "end_month": season_config.kharif.end_month},
        "rabi": {"start_month": season_config.rabi.start_month, "end_month": season_config.rabi.end_month},
    }


async def get_climate_shift(lat: float, lon: float, start_year: int | None = None, end_year: int | None = None, season_config=None) -> dict:
    end_year = end_year or latest_full_year()
    start_year = start_year or 2001
    seasons = _season_config_to_dict(season_config)

    power = await fetch_power_daily(lat, lon, start_year, end_year)
    if not power["ok"]:
        return {
            "error": True,
            "source": source_meta("nasa_power", "unavailable", power.get("error"), False),
        }

    analysis = analyze_climate_shift(power["series"], start_year, end_year, seasons)
    analysis["seasons_used"] = {
        "kharif": {"name": "kharif", **seasons["kharif"]},
        "rabi": {"name": "rabi", **seasons["rabi"]},
    }
    analysis["source"] = source_meta("nasa_power", "ok", None, power.get("cache_hit", False))
    analysis["_power_series"] = power["series"]  # internal use by rotation scoring, stripped before response
    analysis["error"] = False
    return analysis


async def get_soil_profile(lat: float, lon: float) -> dict:
    soil = await fetch_soil_profile(lat, lon)
    if not soil["ok"]:
        return {
            "layers": [],
            "status": "unavailable",
            "message": soil.get("error"),
            "source": source_meta("isric_soilgrids", "unavailable", soil.get("error"), False),
        }

    if soil["all_null"]:
        return {
            "layers": soil["layers"],
            "status": "manual_input_needed",
            "message": (
                "ISRIC SoilGrids returned HTTP 200 but null values for every property/depth at this "
                "location. This looks like an upstream data outage rather than a request error "
                "(verified against multiple real-world test points). Please enter soil values manually."
            ),
            "source": source_meta("isric_soilgrids", "manual_input_needed", "all properties null from upstream", soil.get("cache_hit", False)),
        }

    if soil.get("any_null"):
        return {
            "layers": soil["layers"],
            "status": "partial",
            "message": "Some soil properties/depths were unavailable from ISRIC SoilGrids for this location.",
            "source": source_meta("isric_soilgrids", "partial", "some properties null from upstream", soil.get("cache_hit", False)),
        }

    return {
        "layers": soil["layers"],
        "status": "ok",
        "message": None,
        "source": source_meta("isric_soilgrids", "ok", None, soil.get("cache_hit", False)),
    }


async def get_ndvi_summary(lat: float, lon: float, start_date: str | None = None, end_date: str | None = None) -> dict:
    if end_date is None:
        # ORNL's MOD13Q1 processing lag can run well beyond a month, so a
        # too-recent default window risks a 400/empty response; 120 days
        # back is a safer default when the caller doesn't pin exact dates.
        end_date = (dt.datetime.utcnow().date() - dt.timedelta(days=120)).isoformat()
    if start_date is None:
        start_date = (dt.date.fromisoformat(end_date) - dt.timedelta(days=730)).isoformat()

    ndvi = await fetch_ndvi_timeseries(lat, lon, start_date, end_date)
    if not ndvi["ok"]:
        return {
            "period_start": start_date,
            "period_end": end_date,
            "points": [],
            "mean_ndvi_good_quality": None,
            "pct_usable": None,
            "status": "unavailable",
            "message": ndvi.get("error"),
            "source": source_meta("ornl_modis_mod13q1", "unavailable", ndvi.get("error"), False),
        }

    points = ndvi["points"]
    usable_values = [p["ndvi"] for p in points if p["usable"]]
    mean_ndvi = round(sum(usable_values) / len(usable_values), 4) if usable_values else None
    pct_usable = round(100 * len(usable_values) / len(points), 1) if points else None

    status = "ok"
    message = None
    if points and not usable_values:
        status = "unavailable"
        message = "No composites in this window passed quality filtering (all cloudy/snow/marginal)."
    elif pct_usable is not None and pct_usable < 100:
        status = "partial"
        message = f"{len(points) - len(usable_values)} of {len(points)} composites were low quality and excluded from the mean"

    return {
        "period_start": start_date,
        "period_end": end_date,
        "points": points,
        "mean_ndvi_good_quality": mean_ndvi,
        "pct_usable": pct_usable,
        "status": status,
        "message": message,
        "source": source_meta("ornl_modis_mod13q1", "ok", None, ndvi.get("cache_hit", False)),
    }


def get_crops_list() -> dict:
    crops = load_crops()
    return {"crops": crops, "count": len(crops)}


async def _climatology_and_soil_for_rotations(lat: float, lon: float, season_config=None) -> tuple:
    climate = await get_climate_shift(lat, lon, season_config=season_config)
    soil = await get_soil_profile(lat, lon)

    warnings = []
    climatology = None
    if not climate.get("error"):
        climatology = build_doy_climatology(climate["_power_series"], recent_start_year=2013)
    else:
        warnings.append(f"climate: {climate['source']['message'] or 'data unavailable'}; rotation scoring used neutral water/heat defaults.")

    soil_layers = None
    if soil["status"] == "ok":
        soil_layers = soil["layers"]
    else:
        warnings.append(f"soil: {soil['message']}")

    return climatology, soil_layers, warnings


async def score_rotations(lat: float, lon: float, current_crops: list[str], priorities: dict, season_config=None, top_n: int = 10) -> dict:
    climatology, soil_layers, warnings = await _climatology_and_soil_for_rotations(lat, lon, season_config)
    result = score_all_rotations(climatology, soil_layers, priorities, current_crops, lat, top_n)
    message = "; ".join(warnings) if warnings else None
    result["source"] = source_meta("sky_to_soil_rotation_optimizer", "ok" if not warnings else "partial", message, False)
    return result


async def run_stress_test(lat: float, lon: float, current_crops: list[str], priorities: dict, delta_temp_c: float, rainfall_change_pct: float, top_n: int = 10) -> dict:
    climatology, soil_layers, warnings = await _climatology_and_soil_for_rotations(lat, lon)
    result = stress_test_rotations(climatology, soil_layers, priorities, current_crops, lat, delta_temp_c, rainfall_change_pct, top_n)
    message = "; ".join(warnings) if warnings else None
    result["source"] = source_meta("sky_to_soil_rotation_optimizer", "ok" if not warnings else "partial", message, False)
    return result
