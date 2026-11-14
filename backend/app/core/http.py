"""Shared async HTTP helper: retries with backoff, consistent timeout."""

from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import get_settings


class UpstreamError(Exception):
    """Raised when an upstream data source cannot be reached after retries."""


def _retrying(max_retries: int):
    return retry(
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError, httpx.TimeoutException)),
        reraise=True,
    )


async def get_json(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    timeout_seconds: float | None = None,
    max_retries: int | None = None,
) -> dict:
    """GET a URL and return parsed JSON, retrying transient failures.

    Raises UpstreamError if every retry attempt fails. `timeout_seconds` /
    `max_retries` let a slow or flaky upstream (e.g. ISRIC SoilGrids) use a
    tighter bound than the global default, so one bad source can't make a
    request hang for minutes.
    """
    settings = get_settings()
    timeout = timeout_seconds if timeout_seconds is not None else settings.http_timeout_seconds
    retries = max_retries if max_retries is not None else settings.http_max_retries

    @_retrying(retries)
    async def _do():
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            return resp.json()

    try:
        return await _do()
    except Exception as exc:  # noqa: BLE001 - we intentionally convert any failure
        raise UpstreamError(f"GET {url} failed after retries: {exc}") from exc
