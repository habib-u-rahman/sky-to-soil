"""Sky-to-Soil backend entrypoint.

Run locally with: uvicorn app.main:app --reload
See backend/README.md for full setup instructions.
"""

from __future__ import annotations

import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.config import get_settings
from app.routers import advisor, climate, crops, farm, health, ndvi, report, rotations, soil

app = FastAPI(
    title="Sky-to-Soil API",
    description="NASA Earth observation + soil + crop decision support for crop rotation planning.",
    version="0.1.0",
)

settings = get_settings()

VERCEL_PREVIEW_RE = re.compile(r"^https://([a-z0-9-]+\.)*vercel\.app$")


class VercelPreviewCORSMiddleware(BaseHTTPMiddleware):
    """Allows any *.vercel.app origin (preview deployments have unpredictable
    subdomains) in addition to the fixed allow-list handled by CORSMiddleware."""

    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        response = await call_next(request)
        if origin and VERCEL_PREVIEW_RE.match(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
        return response


app.add_middleware(VercelPreviewCORSMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(climate.router)
app.include_router(soil.router)
app.include_router(ndvi.router)
app.include_router(crops.router)
app.include_router(rotations.router)
app.include_router(farm.router)
app.include_router(advisor.router)
app.include_router(report.router)
