from fastapi import APIRouter, HTTPException, Query

from app import services
from app.core.demo import load_demo_analysis
from app.schemas import (
    RotationScoreRequest,
    RotationsScoreResponse,
    RotationsStressTestResponse,
    StressTestRequest,
)

router = APIRouter()


@router.post("/rotations/score", response_model=RotationsScoreResponse)
async def post_rotations_score(body: RotationScoreRequest, demo: bool = Query(False)):
    if demo:
        demo_data = load_demo_analysis()
        if demo_data and demo_data.get("rotations"):
            return demo_data["rotations"]
        raise HTTPException(status_code=503, detail="Demo data not built yet. Run: python -m app.scripts.build_demo")

    priorities = body.priorities.model_dump()
    result = await services.score_rotations(
        body.location.lat, body.location.lon, body.current_crops, priorities, body.season_config, body.top_n
    )
    result["location"] = body.location.model_dump()
    result["priorities"] = body.priorities
    return result


@router.post("/rotations/stress-test", response_model=RotationsStressTestResponse)
async def post_rotations_stress_test(body: StressTestRequest, demo: bool = Query(False)):
    if demo:
        demo_data = load_demo_analysis()
        if demo_data and demo_data.get("stress_test"):
            return demo_data["stress_test"]
        raise HTTPException(status_code=503, detail="Demo data not built yet. Run: python -m app.scripts.build_demo")

    priorities = body.priorities.model_dump()
    result = await services.run_stress_test(
        body.location.lat,
        body.location.lon,
        body.current_crops,
        priorities,
        body.scenario.delta_temp_c,
        body.scenario.rainfall_change_pct,
        body.top_n,
    )
    result["location"] = body.location.model_dump()
    result["scenario"] = body.scenario
    return result
