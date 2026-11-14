"""Groq model discovery + chat-completion helper for the AI Agronomist.

Never logs or returns the API key itself -- only model ids and completions.
"""

from __future__ import annotations

import asyncio
import json
from functools import lru_cache

from groq import AsyncGroq

from app.core.config import get_settings

PREFERRED_MODEL = "openai/gpt-oss-120b"

# Preference order used to pick a fallback model if PREFERRED_MODEL is not
# present on the account, and to pick the single retry model used when the
# primary model call itself fails at request time.
FALLBACK_CANDIDATES = [
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]

TEMPERATURE = 0


def _client() -> AsyncGroq:
    settings = get_settings()
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not set")
    return AsyncGroq(api_key=settings.groq_api_key)


@lru_cache
def _cached_model_ids() -> tuple[str, ...]:
    """Synchronous, cached listing of model ids available on this account.
    Cached for the process lifetime -- model availability doesn't change
    within a single deployment's uptime, and this avoids an extra network
    round-trip on every advisor request."""
    from groq import Groq

    settings = get_settings()
    if not settings.groq_api_key:
        return ()
    client = Groq(api_key=settings.groq_api_key)
    models = client.models.list()
    return tuple(m.id for m in models.data)


async def list_model_ids() -> list[str]:
    """Async-friendly wrapper around the cached model listing."""
    return list(await asyncio.to_thread(_cached_model_ids))


async def select_models() -> tuple[str, str]:
    """Returns (primary_model, fallback_model). Primary is PREFERRED_MODEL if
    present on the account, else the first available FALLBACK_CANDIDATE.
    Fallback is the first FALLBACK_CANDIDATE that is both present and
    different from the chosen primary (used as the single retry model if the
    primary call fails)."""
    available = set(await list_model_ids())

    if PREFERRED_MODEL in available or not available:
        primary = PREFERRED_MODEL
    else:
        primary = next((m for m in FALLBACK_CANDIDATES if m in available), PREFERRED_MODEL)

    fallback = next(
        (m for m in FALLBACK_CANDIDATES if m != primary and (not available or m in available)),
        FALLBACK_CANDIDATES[0],
    )
    return primary, fallback


async def complete_json(messages: list[dict], max_tokens: int = 3000) -> tuple[dict, str]:
    """Calls Groq chat completions with JSON-object response mode, trying the
    primary model first and falling back to exactly one other model if the
    primary call raises. Returns (parsed_json, model_used).

    reasoning_effort=low is passed via extra_body: the gpt-oss reasoning
    models otherwise spend a large, unbounded share of max_tokens on hidden
    reasoning before emitting the final JSON, which can exhaust the token
    budget and return an empty/invalid completion for anything but very
    short prompts."""
    primary, fallback = await select_models()
    client = _client()

    last_error: Exception | None = None
    for model in (primary, fallback):
        kwargs = {}
        if model.startswith("openai/gpt-oss"):
            kwargs["extra_body"] = {"reasoning_effort": "low"}
        try:
            resp = await client.chat.completions.create(
                model=model,
                temperature=TEMPERATURE,
                response_format={"type": "json_object"},
                max_tokens=max_tokens,
                messages=messages,
                **kwargs,
            )
            content = resp.choices[0].message.content or "{}"
            return _parse_json_object(content), model
        except Exception as exc:  # noqa: BLE001 - deliberately broad: any failure triggers the one fallback retry
            last_error = exc
            continue

    raise RuntimeError(f"Groq completion failed on both primary and fallback models: {last_error}")


def _parse_json_object(content: str) -> dict:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start, end = content.find("{"), content.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(content[start : end + 1])
        raise
