from fastapi import APIRouter, HTTPException, Query

from app import services
from app.core.demo import load_demo_analysis
from app.schemas import NdviSummaryResponse

router = APIRouter()


@router.get("/ndvi", response_model=NdviSummaryResponse)
async def get_ndvi(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    start_date: str | None = Query(None, description="YYYY-MM-DD"),
    end_date: str | None = Query(None, description="YYYY-MM-DD"),
    demo: bool = Query(False),
):
    if demo:
        demo_data = load_demo_analysis()
        if demo_data and demo_data.get("ndvi"):
            return demo_data["ndvi"]
        raise HTTPException(status_code=503, detail="Demo data not built yet. Run: python -m app.scripts.build_demo")

    result = await services.get_ndvi_summary(lat, lon, start_date, end_date)
    result["location"] = {"lat": lat, "lon": lon}
    return result
