"""Helpers for building SourceMeta-shaped dicts consistently across routers."""

from __future__ import annotations

import datetime as dt


def now_iso() -> str:
    return dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def source_meta(source: str, status: str, message: str | None = None, cache_hit: bool = False) -> dict:
    return {
        "source": source,
        "status": status,
        "message": message,
        "cache_hit": cache_hit,
        "fetched_at": now_iso(),
    }
