from fastapi import APIRouter

from app.core.sources import now_iso
from app.schemas import HealthResponse

router = APIRouter()

VERSION = "0.1.0"


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", service="sky-to-soil-backend", version=VERSION, time=now_iso())
