"""Tests for the LangGraph pipeline (collect_facts -> retrieve -> write ->
verify -> rewrite-once -> fallback_template), with the Groq call mocked out
so these run fast and offline. Covers: pass-on-first-try, pass-after-one-
rewrite, and falls-back-after-exhausting-the-rewrite."""

from unittest.mock import AsyncMock

import pytest

from app.advisor import graph as graph_module

BUNDLE = {
    "location": {"lat": 31.42, "lon": 73.08},
    "current_crops": ["wheat", "cotton"],
    "rotation_entry": {
        "rotation": {"Y1_kharif": None, "Y1_rabi": "wheat", "Y2_kharif": None, "Y2_rabi": "wheat"},
        "sub_scores": {"water_fit": 40.5, "heat_risk": 80.0, "soil_health": 31.6, "soil_suitability": 65.0},
        "base_score_0_100": 54.3,
        "priority_weighted_score_0_100": 57.6,
        "reasons": ["A workable rotation."],
        "warnings": ["This rotation likely needs significant supplemental irrigation."],
    },
    "stress_entry": None,
    "climate_block": None,
    "soil_layers": None,
    "per_crop_detail": {"wheat": {"data_available": False}},
    "data_sources": [{"source": "sky_to_soil_rotation_optimizer", "status": "ok"}],
}

GOOD_EXPLAIN_JSON = {
    "farmer_text": "This rotation grows Wheat (bread wheat), scoring 54 out of 100. Confirm with your local extension officer.",
    "technical_note": "Base score 54.3. Confirm with a local extension officer.",
}
BAD_EXPLAIN_JSON = {
    "farmer_text": "This rotation grows Wheat (bread wheat) and Rice. Confirm with your local extension officer.",
    "technical_note": "Rice yields 9999 kg/ha. Confirm with a local extension officer.",
}

GOOD_CHAT_JSON = {
    "answer": "Wheat is in this rotation. Confirm with your local extension officer.",
    "answerable": True,
}


@pytest.fixture(autouse=True)
def _reset_compiled_graph():
    # get_graph() memoizes the compiled StateGraph at module scope; force a
    # fresh compile per test so mocked nodes don't leak between tests.
    graph_module._COMPILED_GRAPH = None
    yield
    graph_module._COMPILED_GRAPH = None


async def test_run_explain_passes_on_first_attempt(monkeypatch):
    mock = AsyncMock(return_value=(GOOD_EXPLAIN_JSON, "openai/gpt-oss-120b"))
    monkeypatch.setattr(graph_module, "complete_json", mock)

    result = await graph_module.run_explain(BUNDLE, ["wheat", "cotton"], "en")

    assert result["verified"] is True
    assert result["rewrites_used"] == 0
    assert result["first_attempt_verified"] is True
    assert result["model_used"] == "openai/gpt-oss-120b"
    assert mock.await_count == 1


async def test_run_explain_recovers_after_one_rewrite(monkeypatch):
    mock = AsyncMock(
        side_effect=[
            (BAD_EXPLAIN_JSON, "openai/gpt-oss-120b"),
            (GOOD_EXPLAIN_JSON, "openai/gpt-oss-120b"),
        ]
    )
    monkeypatch.setattr(graph_module, "complete_json", mock)

    result = await graph_module.run_explain(BUNDLE, ["wheat", "cotton"], "en")

    assert result["verified"] is True
    assert result["rewrites_used"] == 1
    assert result["first_attempt_verified"] is False
    assert mock.await_count == 2


async def test_run_explain_falls_back_after_exhausting_rewrite(monkeypatch):
    mock = AsyncMock(return_value=(BAD_EXPLAIN_JSON, "openai/gpt-oss-120b"))
    monkeypatch.setattr(graph_module, "complete_json", mock)

    result = await graph_module.run_explain(BUNDLE, ["wheat", "cotton"], "en")

    assert result["model_used"] == "fallback_template"
    assert result["verified"] is True  # fallback_template is re-verified and must pass on its own
    assert result["first_attempt_verified"] is False
    assert mock.await_count == 2  # write + one rewrite, then fallback (no further LLM calls)


async def test_run_explain_falls_back_when_groq_raises(monkeypatch):
    # A total Groq outage (both primary and fallback model calls failing)
    # must degrade to the offline template, not crash the whole request.
    mock = AsyncMock(side_effect=RuntimeError("Groq completion failed on both primary and fallback models"))
    monkeypatch.setattr(graph_module, "complete_json", mock)

    result = await graph_module.run_explain(BUNDLE, ["wheat", "cotton"], "en")

    assert result["model_used"] == "fallback_template"
    assert result["verified"] is True
    assert result["first_attempt_verified"] is False


async def test_run_chat_passes_on_first_attempt(monkeypatch):
    mock = AsyncMock(return_value=(GOOD_CHAT_JSON, "openai/gpt-oss-120b"))
    monkeypatch.setattr(graph_module, "complete_json", mock)

    result = await graph_module.run_chat(BUNDLE, ["wheat", "cotton"], "en", "What crop is in this rotation?")

    assert result["verified"] is True
    assert result["answerable"] is True
    assert result["answer"] == GOOD_CHAT_JSON["answer"]
