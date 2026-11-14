"""API-level tests for /advisor/explain and /advisor/chat. Demo mode is
exercised against the real frozen demo_analysis.json (fully offline, no
mocking needed, since it was precomputed by `python -m app.scripts.build_demo`).
Live mode mocks both the upstream data clients and the Groq call so these
stay fast and offline too."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

LIVE_ANALYSIS = {
    "location": {"lat": 31.42, "lon": 73.08},
    "generated_at": "2026-01-01T00:00:00Z",
    "climate": None,
    "soil": None,
    "ndvi": None,
    "rotations": {
        "location": {"lat": 31.42, "lon": 73.08},
        "priorities": {"save_water": 0.25, "build_soil": 0.25, "lower_climate_risk": 0.25, "stay_close_to_current": 0.25, "income_proxy": None},
        "candidates_evaluated": 10,
        "top": [
            {
                "rotation": {"Y1_kharif": None, "Y1_rabi": "wheat", "Y2_kharif": None, "Y2_rabi": "wheat"},
                "sub_scores": {"water_fit": 40.5, "heat_risk": 80.0, "soil_health": 31.6, "soil_suitability": 65.0},
                "base_score_0_100": 54.3,
                "priority_weighted_score_0_100": 57.6,
                "reasons": ["A workable rotation."],
                "warnings": ["This rotation likely needs significant supplemental irrigation."],
            }
        ],
        "pareto_optimal": [],
        "source": {"source": "sky_to_soil_rotation_optimizer", "status": "ok", "message": None, "cache_hit": False, "fetched_at": "2026-01-01T00:00:00Z"},
    },
    "stress_test": None,
    "warnings": [],
}

GOOD_EXPLAIN_JSON = {
    "farmer_text": "This rotation grows Wheat (bread wheat), scoring 54 out of 100. Confirm with your local extension officer.",
    "technical_note": "Base score 54.3. Confirm with a local extension officer.",
}


def _mock_live_sources(monkeypatch):
    async def fake_climate_shift(lat, lon, start_year=None, end_year=None, season_config=None):
        return {"error": True, "source": {"source": "nasa_power", "status": "unavailable", "message": "mocked offline", "cache_hit": False, "fetched_at": "x"}}

    async def fake_soil_profile(lat, lon):
        return {"layers": [], "status": "unavailable", "message": "mocked offline", "source": {"source": "isric_soilgrids", "status": "unavailable", "message": "mocked offline", "cache_hit": False, "fetched_at": "x"}}

    monkeypatch.setattr("app.services.get_climate_shift", fake_climate_shift)
    monkeypatch.setattr("app.services.get_soil_profile", fake_soil_profile)


# --- demo mode (offline, real frozen demo data) -----------------------------

def test_advisor_explain_demo_default_rotation_is_cached_and_verified():
    resp = client.post("/advisor/explain?demo=true", json={"rotation_id": "top_0", "current_crops": ["wheat", "cotton"], "language": "en"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["verified"] is True
    assert body["model_used"] in ("openai/gpt-oss-120b", "openai/gpt-oss-20b", "fallback_template")
    assert body["text"]
    assert body["technical_note"]


def test_advisor_explain_demo_urdu_is_cached_and_verified():
    resp = client.post("/advisor/explain?demo=true", json={"rotation_id": "top_0", "current_crops": ["wheat", "cotton"], "language": "ur"})
    assert resp.status_code == 200
    assert resp.json()["verified"] is True


def test_advisor_explain_demo_uncached_rotation_falls_back_offline():
    # top_4 wasn't precomputed by build_demo (only top_0 is cached) -- this
    # must still return 200 fully offline via the deterministic template.
    resp = client.post("/advisor/explain?demo=true", json={"rotation_id": "top_4", "current_crops": ["wheat", "cotton"], "language": "en"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["model_used"] == "fallback_template"
    assert body["verified"] is True


def test_advisor_chat_demo_cached_sample_question():
    resp = client.post(
        "/advisor/chat?demo=true",
        json={"question": "Why was this rotation recommended for my farm?", "current_crops": ["wheat", "cotton"], "language": "en"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["verified"] is True
    assert body["answer"]


def test_advisor_chat_demo_uncached_question_falls_back_offline():
    resp = client.post(
        "/advisor/chat?demo=true",
        json={"question": "What is the square root of 9999?", "current_crops": ["wheat", "cotton"], "language": "en"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["model_used"] == "fallback_template"
    assert body["answerable"] is False


def test_advisor_demo_mode_requires_no_analysis_body():
    resp = client.post("/advisor/explain?demo=true", json={"rotation_id": "top_0"})
    assert resp.status_code == 200


# --- live mode (mocked upstream + mocked Groq) -------------------------------

def test_advisor_explain_live_requires_analysis_body():
    resp = client.post("/advisor/explain", json={"rotation_id": "top_0"})
    assert resp.status_code == 422


def test_advisor_explain_live_rejects_unknown_rotation_id(monkeypatch):
    _mock_live_sources(monkeypatch)
    resp = client.post("/advisor/explain", json={"analysis": LIVE_ANALYSIS, "rotation_id": "top_99", "current_crops": ["wheat"]})
    assert resp.status_code == 422


def test_advisor_explain_live_end_to_end_with_mocked_groq(monkeypatch):
    _mock_live_sources(monkeypatch)
    monkeypatch.setattr("app.advisor.graph.complete_json", AsyncMock(return_value=(GOOD_EXPLAIN_JSON, "openai/gpt-oss-120b")))

    resp = client.post(
        "/advisor/explain",
        json={"analysis": LIVE_ANALYSIS, "rotation_id": "top_0", "current_crops": ["wheat", "cotton"], "language": "en"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["verified"] is True
    assert body["model_used"] == "openai/gpt-oss-120b"
    assert body["rewrites_used"] == 0
    assert "sky_to_soil_rotation_optimizer" not in body["kb_sources"]  # kb_sources is KB topics, not data sources


def test_advisor_chat_live_end_to_end_with_mocked_groq(monkeypatch):
    _mock_live_sources(monkeypatch)
    good_chat = {"answer": "This rotation includes wheat. Confirm with your local extension officer.", "answerable": True}
    monkeypatch.setattr("app.advisor.graph.complete_json", AsyncMock(return_value=(good_chat, "openai/gpt-oss-120b")))

    resp = client.post(
        "/advisor/chat",
        json={"analysis": LIVE_ANALYSIS, "question": "What crop is in this rotation?", "current_crops": ["wheat", "cotton"], "language": "en"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["verified"] is True
    assert body["answerable"] is True
