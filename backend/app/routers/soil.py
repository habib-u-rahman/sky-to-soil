from fastapi import APIRouter, HTTPException, Query

from app import services
from app.core.demo import load_demo_analysis
from app.core.sources import source_meta
from app.schemas import SoilPresetsResponse, SoilProfileResponse

router = APIRouter()

# Typical representative values per USDA soil texture class, used by the
# frontend to auto-fill soil inputs when ISRIC SoilGrids is unavailable.
# Approximate midpoints, not location-specific -- see `source` below.
SOIL_PRESETS_SOURCE = (
    "Approximate midpoints per USDA-NRCS soil texture class definitions "
    "(clay/sand/silt boundaries) combined with typical pH/organic-carbon/CEC "
    "ranges reported in FAO Soils Portal texture-class guidance. Illustrative "
    "manual-entry defaults, not a substitute for a local soil test."
)

SOIL_PRESETS = [
    {"texture": "sand", "phh2o": 6.5, "clay_pct": 5.0, "sand_pct": 88.0, "silt_pct": 7.0, "soc_g_kg": 5.0, "nitrogen_g_kg": 0.3, "cec_cmol_kg": 5.0},
    {"texture": "sandy_loam", "phh2o": 6.5, "clay_pct": 12.0, "sand_pct": 63.0, "silt_pct": 25.0, "soc_g_kg": 8.0, "nitrogen_g_kg": 0.5, "cec_cmol_kg": 9.0},
    {"texture": "loam", "phh2o": 6.8, "clay_pct": 20.0, "sand_pct": 40.0, "silt_pct": 40.0, "soc_g_kg": 15.0, "nitrogen_g_kg": 1.0, "cec_cmol_kg": 16.0},
    {"texture": "silt_loam", "phh2o": 6.8, "clay_pct": 15.0, "sand_pct": 20.0, "silt_pct": 65.0, "soc_g_kg": 15.0, "nitrogen_g_kg": 1.0, "cec_cmol_kg": 17.0},
    {"texture": "clay_loam", "phh2o": 7.0, "clay_pct": 32.0, "sand_pct": 30.0, "silt_pct": 38.0, "soc_g_kg": 18.0, "nitrogen_g_kg": 1.2, "cec_cmol_kg": 25.0},
    {"texture": "clay", "phh2o": 7.2, "clay_pct": 50.0, "sand_pct": 20.0, "silt_pct": 30.0, "soc_g_kg": 20.0, "nitrogen_g_kg": 1.3, "cec_cmol_kg": 35.0},
]


@router.get("/soil", response_model=SoilProfileResponse)
async def get_soil(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    demo: bool = Query(False),
):
    if demo:
        demo_data = load_demo_analysis()
        if demo_data and demo_data.get("soil"):
            return demo_data["soil"]
        raise HTTPException(status_code=503, detail="Demo data not built yet. Run: python -m app.scripts.build_demo")

    result = await services.get_soil_profile(lat, lon)
    result["location"] = {"lat": lat, "lon": lon}
    return result


@router.get("/soil/presets", response_model=SoilPresetsResponse)
async def get_soil_presets():
    return {
        "presets": SOIL_PRESETS,
        "source": source_meta("usda_fao_texture_class_typical_values", "ok", SOIL_PRESETS_SOURCE, False),
    }
