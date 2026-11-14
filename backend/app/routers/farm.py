import asyncio

from fastapi import APIRouter, HTTPException, Query

from app import services
from app.core.demo import load_demo_analysis
from app.core.sources import now_iso
from app.schemas import FarmAnalyzeRequest, FarmAnalyzeResponse
from app.science.climatology import build_doy_climatology
from app.science.rotation_engine import score_all_rotations, stress_test_rotations

router = APIRouter()


@router.post("/farm/analyze", response_model=FarmAnalyzeResponse)
async def post_farm_analyze(body: FarmAnalyzeRequest, demo: bool = Query(False)):
    if demo:
        demo_data = load_demo_analysis()
        if demo_data:
            return demo_data
        raise HTTPException(status_code=503, detail="Demo data not built yet. Run: python -m app.scripts.build_demo")

    lat, lon = body.location.lat, body.location.lon
    warnings: list[str] = []

    climate_task = services.get_climate_shift(lat, lon, season_config=body.season_config)
    soil_task = services.get_soil_profile(lat, lon)
    ndvi_task = services.get_ndvi_summary(lat, lon)
    climate_raw, soil, ndvi = await asyncio.gather(climate_task, soil_task, ndvi_task)

    climate = None
    climatology = None
    if climate_raw.get("error"):
        warnings.append(f"climate: NASA POWER unavailable ({climate_raw['source']['message']})")
    else:
        climatology = build_doy_climatology(climate_raw["_power_series"], recent_start_year=2013)
        climate_raw.pop("_power_series", None)
        climate_raw.pop("error", None)
        climate_raw["location"] = {"lat": lat, "lon": lon}
        climate = climate_raw

    soil["location"] = {"lat": lat, "lon": lon}
    if soil["status"] != "ok":
        warnings.append(f"soil: {soil['message']}")

    ndvi["location"] = {"lat": lat, "lon": lon}
    if ndvi["status"] not in ("ok",):
        warnings.append(f"ndvi: {ndvi['message'] or ndvi['status']}")

    soil_layers = soil["layers"] if soil["status"] == "ok" else None
    priorities = body.priorities.model_dump()

    rotations_raw = score_all_rotations(climatology, soil_layers, priorities, body.current_crops, lat, body.top_n)
    rotations_raw["location"] = {"lat": lat, "lon": lon}
    rotations_raw["priorities"] = body.priorities
    rotations_raw["source"] = {
        "source": "sky_to_soil_rotation_optimizer",
        "status": "ok" if climatology is not None and soil_layers is not None else "partial",
        "message": None,
        "cache_hit": False,
        "fetched_at": now_iso(),
    }

    stress_test = None
    if body.include_stress_test:
        stress_raw = stress_test_rotations(
            climatology, soil_layers, priorities, body.current_crops, lat, 1.5, -15.0, body.top_n
        )
        stress_raw["location"] = {"lat": lat, "lon": lon}
        stress_raw["scenario"] = {"delta_temp_c": 1.5, "rainfall_change_pct": -15.0}
        stress_raw["source"] = rotations_raw["source"]
        stress_test = stress_raw

    return {
        "location": {"lat": lat, "lon": lon},
        "generated_at": now_iso(),
        "climate": climate,
        "soil": soil,
        "ndvi": ndvi,
        "rotations": rotations_raw,
        "stress_test": stress_test,
        "warnings": warnings,
    }
