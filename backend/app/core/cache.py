"""Disk-backed cache for upstream API responses (diskcache), keyed by a
string the caller builds (e.g. "power:31.42:73.08:2001:2024")."""

from __future__ import annotations

from diskcache import Cache

from app.core.config import CACHE_DIR, get_settings

CACHE_DIR.mkdir(parents=True, exist_ok=True)
_cache = Cache(str(CACHE_DIR))


def cache_get(key: str):
    return _cache.get(key, default=None)


def cache_set(key: str, value) -> None:
    settings = get_settings()
    _cache.set(key, value, expire=settings.cache_ttl_seconds)


def cache_key(*parts) -> str:
    return ":".join(str(p) for p in parts)
