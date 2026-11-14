from fastapi import APIRouter, HTTPException, Query

from app import services
from app.core.demo import load_demo_analysis
from app.schemas import ClimateShiftResponse

router = APIRouter()


@router.get("/climate", response_model=ClimateShiftResponse)
async def get_climate(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    start_year: int | None = Query(None, ge=2001),
    end_year: int | None = Query(None),
    demo: bool = Query(False),
):
    if demo:
        demo_data = load_demo_analysis()
        if demo_data and demo_data.get("climate"):
            return demo_data["climate"]
        raise HTTPException(status_code=503, detail="Demo data not built yet. Run: python -m app.scripts.build_demo")

    result = await services.get_climate_shift(lat, lon, start_year, end_year)
    if result.get("error"):
        raise HTTPException(status_code=502, detail=f"NASA POWER unavailable: {result['source']['message']}")

    result.pop("_power_series", None)
    result.pop("error", None)
    result["location"] = {"lat": lat, "lon": lon}
    return result
