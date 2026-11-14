"""Builds the compact `facts` object that is the ONLY source of numbers the
AI Agronomist is allowed to use. Two ways to produce the raw "bundle" this is
assembled from:

- `build_bundle_live`: fetches climate + soil for a real location (reuses
  `app.services`, same as `/farm/analyze`), then computes per-crop water
  deficit / heat-stress-day detail for just the crops in the chosen rotation.
- `resolve_from_demo`: pulls everything from the frozen demo analysis file
  (including precomputed per-crop detail -- see app/scripts/build_demo.py),
  so demo mode never touches the network.
"""

from __future__ import annotations

from app import services
from app.data.crop_repo import SOWING_START, crops_by_id
from app.science.climatology import build_doy_climatology, extract_window
from app.science.crop_water import crop_seasonal_water_need
from app.science.et0 import et0_hargreaves
from app.science.heat_stress import count_heat_stress_days
from app.science.soil_suitability import classify_texture, weighted_profile_mean

SLOTS = ["Y1_kharif", "Y1_rabi", "Y2_kharif", "Y2_rabi"]


def compute_crop_climate_detail(crop: dict, climatology: dict[int, dict] | None, lat: float) -> dict:
    """Per-crop seasonal water deficit + heat-stress-day counts for its
    specific sowing window, independent of soil. Mirrors the inputs the
    rotation engine scores on, but reports raw mm/day values instead of a
    0-100 score, since the advisor needs real numbers to cite."""
    if climatology is None or crop["id"] not in SOWING_START:
        return {"data_available": False}

    start_month, start_day = SOWING_START[crop["id"]]
    window = extract_window(climatology, start_month, start_day, crop["duration_days"])

    tmax = window["tmax"]
    tmin = window["tmin"]
    tmean = window["tmean"]
    precip = [p if p is not None else 0.0 for p in window["precip"]]
    start_doy = window["start_doy"]

    et0_daily = []
    for i in range(len(tmax)):
        if tmax[i] is None or tmin[i] is None or tmean[i] is None:
            et0_daily.append(0.0)
            continue
        doy = ((start_doy - 1 + i) % 365) + 1
        et0_daily.append(et0_hargreaves(tmax[i], tmin[i], tmean[i], doy, lat))

    water = crop_seasonal_water_need(crop["kc_stages"], et0_daily, precip)
    tmax_for_heat = [t if t is not None else 0.0 for t in tmax]
    heat = count_heat_stress_days(tmax_for_heat, crop["kc_stages"], crop["heat_sensitive_stage"], crop["critical_temp_c"])

    return {
        "data_available": True,
        "etc_total_mm": water["etc_total_mm"],
        "total_rainfall_mm": water["total_rainfall_mm"],
        "effective_rainfall_mm": water["effective_rainfall_mm"],
        "water_deficit_mm": water["water_deficit_mm"],
        "heat_stress_days": heat["days_tmax_gt_critical"],
        "heat_window_length_days": heat["window_length_days"],
        "pct_heat_window_days_hot": heat["pct_window_days_hot"],
        "critical_temp_c": crop["critical_temp_c"],
    }


async def build_bundle_live(lat: float, lon: float, current_crops: list[str], rotation_entry: dict, stress_entry: dict | None) -> dict:
    climate_raw = await services.get_climate_shift(lat, lon)
    soil = await services.get_soil_profile(lat, lon)

    climatology = None
    climate_block = None
    if not climate_raw.get("error"):
        climatology = build_doy_climatology(climate_raw["_power_series"], recent_start_year=2013)
        climate_block = {
            "baseline": climate_raw["baseline"],
            "recent": climate_raw["recent"],
            "deltas": climate_raw["deltas"],
            "trends": climate_raw["trends"],
        }

    soil_layers = soil["layers"] if soil["status"] == "ok" else None

    crop_lookup = crops_by_id()
    rotation_crop_ids = {slot: cid for slot, cid in rotation_entry["rotation"].items() if cid}
    per_crop_detail = {
        cid: compute_crop_climate_detail(crop_lookup[cid], climatology, lat)
        for cid in set(rotation_crop_ids.values())
        if cid in crop_lookup
    }

    data_sources = [
        {"source": "nasa_power", "status": "ok" if climate_block else "unavailable"},
        {"source": "isric_soilgrids", "status": soil["status"]},
        {"source": "sky_to_soil_rotation_optimizer", "status": "ok"},
    ]

    return {
        "location": {"lat": lat, "lon": lon},
        "current_crops": current_crops,
        "rotation_entry": rotation_entry,
        "stress_entry": stress_entry,
        "climate_block": climate_block,
        "soil_layers": soil_layers,
        "per_crop_detail": per_crop_detail,
        "data_sources": data_sources,
    }


def find_rotation_entry(rotations_block: dict, rotation_id: str) -> dict:
    list_name, _, idx_str = rotation_id.partition("_")
    key = {"top": "top", "pareto": "pareto_optimal"}.get(list_name)
    if key is None or not idx_str.isdigit():
        raise ValueError(f"Unrecognised rotation_id '{rotation_id}'; expected e.g. 'top_0' or 'pareto_0'")
    entries = rotations_block.get(key) or []
    idx = int(idx_str)
    if idx >= len(entries):
        raise ValueError(f"rotation_id '{rotation_id}' is out of range ({len(entries)} entries in '{key}')")
    return entries[idx]


def find_stress_entry(stress_test_block: dict | None, rotation_plan: dict) -> dict | None:
    if not stress_test_block:
        return None
    for result in stress_test_block.get("results", []):
        if result["rotation"] == rotation_plan:
            return result
    return None


def resolve_from_demo(demo_data: dict, rotation_id: str, current_crops: list[str]) -> dict:
    rotation_entry = find_rotation_entry(demo_data["rotations"], rotation_id)
    stress_entry = find_stress_entry(demo_data.get("stress_test"), rotation_entry["rotation"])

    climate = demo_data.get("climate")
    climate_block = None
    if climate:
        climate_block = {
            "baseline": climate["baseline"],
            "recent": climate["recent"],
            "deltas": climate["deltas"],
            "trends": climate["trends"],
        }

    soil = demo_data.get("soil") or {}
    soil_layers = soil.get("layers") if soil.get("status") == "ok" else None

    crop_lookup = crops_by_id()
    rotation_crop_ids = {slot: cid for slot, cid in rotation_entry["rotation"].items() if cid}

    per_crop_detail = demo_data.get("advisor_crop_detail") or {}
    missing = [cid for cid in rotation_crop_ids.values() if cid not in per_crop_detail]
    if missing:
        # Precomputed cache didn't cover this crop (e.g. demo file predates
        # it) -- compute on the fly from the demo location's climatology so
        # the facts object is never silently incomplete.
        climatology = None
        if climate and "_power_series" in climate:
            climatology = build_doy_climatology(climate["_power_series"], recent_start_year=2013)
        lat = demo_data["location"]["lat"]
        for cid in missing:
            if cid in crop_lookup:
                per_crop_detail[cid] = compute_crop_climate_detail(crop_lookup[cid], climatology, lat)

    data_sources = [
        {"source": "nasa_power", "status": "ok" if climate_block else "unavailable"},
        {"source": "isric_soilgrids", "status": soil.get("status", "unavailable")},
        {"source": "sky_to_soil_rotation_optimizer", "status": "ok"},
    ]

    return {
        "location": demo_data["location"],
        "current_crops": current_crops,
        "rotation_entry": rotation_entry,
        "stress_entry": stress_entry,
        "climate_block": climate_block,
        "soil_layers": soil_layers,
        "per_crop_detail": {cid: per_crop_detail[cid] for cid in rotation_crop_ids.values() if cid in per_crop_detail},
        "data_sources": data_sources,
    }


def _soil_summary(soil_layers: list[dict] | None) -> dict:
    if not soil_layers:
        return {"data_available": False}
    ph = weighted_profile_mean(soil_layers, "phh2o")
    clay = weighted_profile_mean(soil_layers, "clay_pct")
    sand = weighted_profile_mean(soil_layers, "sand_pct")
    silt = weighted_profile_mean(soil_layers, "silt_pct")
    return {
        "data_available": True,
        "ph": ph,
        "texture_class": classify_texture(clay, sand, silt),
        "clay_pct": clay,
        "sand_pct": sand,
        "silt_pct": silt,
        "soc_g_kg": weighted_profile_mean(soil_layers, "soc_g_kg"),
        "nitrogen_g_kg": weighted_profile_mean(soil_layers, "nitrogen_g_kg"),
        "cec_cmol_kg": weighted_profile_mean(soil_layers, "cec_cmol_kg"),
    }


def _climate_shift_summary(climate_block: dict | None) -> dict:
    if not climate_block:
        return {"data_available": False}
    baseline, recent, deltas = climate_block["baseline"], climate_block["recent"], climate_block["deltas"]
    return {
        "data_available": True,
        "baseline_period": f"{baseline['start_year']}-{baseline['end_year']}",
        "recent_period": f"{recent['start_year']}-{recent['end_year']}",
        "mean_tmax_c_baseline": baseline.get("mean_tmax_c"),
        "mean_tmax_c_recent": recent.get("mean_tmax_c"),
        "delta_tmax_c": deltas.get("mean_tmax_c"),
        "mean_tmin_c_baseline": baseline.get("mean_tmin_c"),
        "mean_tmin_c_recent": recent.get("mean_tmin_c"),
        "delta_tmin_c": deltas.get("mean_tmin_c"),
        "kharif_rainfall_mm_baseline": baseline.get("seasonal_rainfall_mm", {}).get("kharif_mm"),
        "kharif_rainfall_mm_recent": recent.get("seasonal_rainfall_mm", {}).get("kharif_mm"),
        "rabi_rainfall_mm_baseline": baseline.get("seasonal_rainfall_mm", {}).get("rabi_mm"),
        "rabi_rainfall_mm_recent": recent.get("seasonal_rainfall_mm", {}).get("rabi_mm"),
        "root_zone_wetness_baseline": baseline.get("mean_root_zone_wetness"),
        "root_zone_wetness_recent": recent.get("mean_root_zone_wetness"),
        "trends": [
            {
                "variable": t["variable"],
                "direction": t["mk_trend"],
                "significant": t["significant_at_0_10"],
                "sen_slope_per_year": t["sen_slope_per_year"],
            }
            for t in climate_block.get("trends", [])
        ],
    }


def assemble_facts(bundle: dict) -> dict:
    """Pure, synchronous: reshapes a raw bundle (live- or demo-sourced) into
    the compact facts object passed to retrieval/write/verify."""
    rotation_entry = bundle["rotation_entry"]
    crop_lookup = crops_by_id()

    rotation_crops = {
        slot: crop_lookup[cid]["name"] for slot, cid in rotation_entry["rotation"].items() if cid and cid in crop_lookup
    }
    rotation_crop_ids = {slot: cid for slot, cid in rotation_entry["rotation"].items() if cid}

    per_crop = {}
    for cid in set(rotation_crop_ids.values()):
        crop = crop_lookup.get(cid)
        if crop is None:
            continue
        detail = bundle["per_crop_detail"].get(cid, {"data_available": False})
        per_crop[cid] = {
            "name": crop["name"],
            "slot": next(s for s, c in rotation_crop_ids.items() if c == cid),
            "family": crop["family"],
            "n_fixing": crop["n_fixing"],
            "residue_contribution": crop["residue_contribution"],
            **detail,
        }

    stress_entry = bundle.get("stress_entry")
    stress_summary = None
    if stress_entry:
        stress_summary = {
            "data_available": True,
            "delta_temp_c": 1.5,
            "rainfall_change_pct": -15.0,
            "baseline_score_0_100": stress_entry["baseline_score_0_100"],
            "stressed_score_0_100": stress_entry["stressed_score_0_100"],
            "score_drop": stress_entry["score_drop"],
            "resilience_score_0_100": stress_entry["resilience_score_0_100"],
        }

    return {
        "location": bundle["location"],
        "current_crops": bundle["current_crops"],
        "rotation_crops": rotation_crops,
        "per_crop": per_crop,
        "rotation_score": {
            "base_score_0_100": rotation_entry["base_score_0_100"],
            "priority_weighted_score_0_100": rotation_entry["priority_weighted_score_0_100"],
            "sub_scores": rotation_entry["sub_scores"],
            "reasons": rotation_entry["reasons"],
            "warnings": rotation_entry["warnings"],
        },
        "stress_test": stress_summary or {"data_available": False},
        "soil": _soil_summary(bundle["soil_layers"]),
        "climate_shift": _climate_shift_summary(bundle["climate_block"]),
        "data_sources": bundle["data_sources"],
    }
