"""Sky-to-Soil backend entrypoint.

Run locally with: uvicorn app.main:app --reload
See backend/README.md for full setup instructions.
"""

from __future__ import annotations

import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.datastructures import MutableHeaders

from app.core.config import get_settings
from app.routers import advisor, climate, crops, farm, health, ndvi, report, rotations, soil

app = FastAPI(
    title="Sky-to-Soil API",
    description="NASA Earth observation + soil + crop decision support for crop rotation planning.",
    version="0.1.0",
)

settings = get_settings()

VERCEL_PREVIEW_RE = re.compile(r"^https://([a-z0-9-]+\.)*vercel\.app$")


class VercelPreviewCORSMiddleware:
    """Allows any *.vercel.app origin (preview deployments have unpredictable
    subdomains) in addition to the fixed allow-list handled by CORSMiddleware.

    Pure ASGI (not `BaseHTTPMiddleware`) deliberately: `BaseHTTPMiddleware`
    buffers/re-streams the whole response through an in-memory channel,
    which was observed (verified live, 2026-11-14) to intermittently drop
    `CORSMiddleware`'s own `Access-Control-Allow-Origin` header -- but only
    for POST /report/pdf's raw-bytes `Response` with a `Content-Disposition`
    header, and only for the real browser request, not curl/http.client --
    causing the actual PDF POST (not the preflight) to fail client-side with
    a CORS error after a real response had already left the server. Plain
    ASGI middleware just forwards messages through `send`, so it can't
    perturb timing/framing for any other middleware in the stack.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        origin = next((v.decode("latin-1") for k, v in scope.get("headers", []) if k == b"origin"), None)

        if not origin or not VERCEL_PREVIEW_RE.match(origin):
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(raw=message["headers"])
                headers["Access-Control-Allow-Origin"] = origin
                headers.append("Vary", "Origin")
            await send(message)

        await self.app(scope, receive, send_wrapper)


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
