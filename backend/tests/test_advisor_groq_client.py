"""Tests for model selection in app.advisor.groq_client. The actual Groq
network calls are mocked out -- these only exercise the picking logic."""

from unittest.mock import AsyncMock

import pytest

from app.advisor import groq_client


@pytest.fixture(autouse=True)
def _clear_model_cache():
    groq_client._cached_model_ids.cache_clear()
    yield
    groq_client._cached_model_ids.cache_clear()


async def test_select_models_prefers_gpt_oss_120b_when_present(monkeypatch):
    monkeypatch.setattr(
        groq_client, "list_model_ids", AsyncMock(return_value=["openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.3-70b-versatile"])
    )
    primary, fallback = await groq_client.select_models()
    assert primary == "openai/gpt-oss-120b"
    assert fallback == "openai/gpt-oss-20b"


async def test_select_models_falls_back_to_candidate_when_preferred_model_absent(monkeypatch):
    monkeypatch.setattr(groq_client, "list_model_ids", AsyncMock(return_value=["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]))
    primary, fallback = await groq_client.select_models()
    assert primary == "llama-3.3-70b-versatile"
    assert fallback != primary


async def test_select_models_defaults_to_preferred_when_listing_is_empty(monkeypatch):
    monkeypatch.setattr(groq_client, "list_model_ids", AsyncMock(return_value=[]))
    primary, fallback = await groq_client.select_models()
    assert primary == groq_client.PREFERRED_MODEL
    assert fallback != primary


async def test_complete_json_retries_fallback_model_on_primary_failure(monkeypatch):
    monkeypatch.setattr(groq_client, "select_models", AsyncMock(return_value=("model-a", "model-b")))

    class FakeMessage:
        content = '{"ok": true}'

    class FakeChoice:
        message = FakeMessage()

    class FakeResponse:
        choices = [FakeChoice()]

    call_log = []

    class FakeCompletions:
        async def create(self, model, **kwargs):
            call_log.append(model)
            if model == "model-a":
                raise RuntimeError("primary down")
            return FakeResponse()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setattr(groq_client, "_client", lambda: FakeClient())

    parsed, model_used = await groq_client.complete_json([{"role": "user", "content": "hi"}])
    assert parsed == {"ok": True}
    assert model_used == "model-b"
    assert call_log == ["model-a", "model-b"]


async def test_complete_json_raises_when_both_models_fail(monkeypatch):
    monkeypatch.setattr(groq_client, "select_models", AsyncMock(return_value=("model-a", "model-b")))

    class FakeCompletions:
        async def create(self, model, **kwargs):
            raise RuntimeError(f"{model} down")

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    monkeypatch.setattr(groq_client, "_client", lambda: FakeClient())

    with pytest.raises(RuntimeError):
        await groq_client.complete_json([{"role": "user", "content": "hi"}])
