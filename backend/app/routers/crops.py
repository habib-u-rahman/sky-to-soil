from fastapi import APIRouter

from app import services
from app.schemas import CropsListResponse

router = APIRouter()


@router.get("/crops", response_model=CropsListResponse)
async def get_crops():
    return services.get_crops_list()
