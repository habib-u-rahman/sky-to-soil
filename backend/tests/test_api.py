"""API-level tests using FastAPI's TestClient. Upstream clients are
monkeypatched so these run fast and offline (no real network calls) --
real-API verification happens separately (see README / PR notes)."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "sky-to-soil-backend"


def test_crops_returns_14_crops():
    resp = client.get("/crops")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 14
    assert len(body["crops"]) == 14
    ids = {c["id"] for c in body["crops"]}
    assert "wheat" in ids and "chickpea" in ids and "sugarcane" in ids


def test_soil_returns_manual_input_needed_when_all_null(monkeypatch):
    async def fake_fetch_soil_profile(lat, lon):
        return {
            "ok": True,
            "all_null": True,
            "any_null": True,
            "layers": [{"depth": d, "phh2o": None, "clay_pct": None, "sand_pct": None, "silt_pct": None, "soc_g_kg": None, "nitrogen_g_kg": None, "cec_cmol_kg": None} for d in ["0-5cm", "5-15cm", "15-30cm"]],
            "cache_hit": False,
        }

    monkeypatch.setattr("app.services.fetch_soil_profile", fake_fetch_soil_profile)

    resp = client.get("/soil", params={"lat": 31.42, "lon": 73.08})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "manual_input_needed"
    assert body["source"]["status"] == "manual_input_needed"


def test_soil_unavailable_when_upstream_fails(monkeypatch):
    async def fake_fetch_soil_profile(lat, lon):
        return {"ok": False, "error": "boom", "cache_hit": False}

    monkeypatch.setattr("app.services.fetch_soil_profile", fake_fetch_soil_profile)

    resp = client.get("/soil", params={"lat": 31.42, "lon": 73.08})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "unavailable"


def test_climate_502_when_power_unreachable(monkeypatch):
    async def fake_fetch_power_daily(lat, lon, start_year=None, end_year=None):
        return {"ok": False, "error": "nasa power down", "cache_hit": False}

    monkeypatch.setattr("app.services.fetch_power_daily", fake_fetch_power_daily)

    resp = client.get("/climate", params={"lat": 31.42, "lon": 73.08})
    assert resp.status_code == 502


def test_rotations_score_validation_error_on_bad_priority():
    resp = client.post(
        "/rotations/score",
        json={"location": {"lat": 31.42, "lon": 73.08}, "priorities": {"save_water": 5.0}},
    )
    assert resp.status_code == 422  # save_water must be <= 1


def test_rotations_score_end_to_end_with_mocked_sources(monkeypatch):
    async def fake_climate_shift(lat, lon, start_year=None, end_year=None, season_config=None):
        return {
            "error": True,
            "source": {"source": "nasa_power", "status": "unavailable", "message": "mocked offline", "cache_hit": False, "fetched_at": "x"},
        }

    async def fake_soil_profile(lat, lon):
        return {
            "layers": [],
            "status": "unavailable",
            "message": "mocked offline",
            "source": {"source": "isric_soilgrids", "status": "unavailable", "message": "mocked offline", "cache_hit": False, "fetched_at": "x"},
        }

    monkeypatch.setattr("app.services.get_climate_shift", fake_climate_shift)
    monkeypatch.setattr("app.services.get_soil_profile", fake_soil_profile)

    resp = client.post(
        "/rotations/score",
        json={
            "location": {"lat": 31.42, "lon": 73.08},
            "current_crops": ["wheat"],
            "priorities": {"save_water": 0.25, "build_soil": 0.25, "lower_climate_risk": 0.25, "stay_close_to_current": 0.25},
            "top_n": 3,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["top"]) == 3
    assert body["source"]["status"] == "partial"
    assert body["candidates_evaluated"] > 1000


def test_farm_analyze_returns_partial_results_with_warnings(monkeypatch):
    async def fake_climate_shift(lat, lon, start_year=None, end_year=None, season_config=None):
        return {
            "error": True,
            "source": {"source": "nasa_power", "status": "unavailable", "message": "mocked offline", "cache_hit": False, "fetched_at": "x"},
        }

    async def fake_soil_profile(lat, lon):
        return {
            "layers": [],
            "status": "unavailable",
            "message": "mocked offline",
            "source": {"source": "isric_soilgrids", "status": "unavailable", "message": "mocked offline", "cache_hit": False, "fetched_at": "x"},
        }

    async def fake_ndvi_summary(lat, lon, start_date=None, end_date=None):
        return {
            "period_start": "2023-01-01",
            "period_end": "2023-03-01",
            "points": [],
            "mean_ndvi_good_quality": None,
            "pct_usable": None,
            "status": "unavailable",
            "message": "mocked offline",
            "source": {"source": "ornl_modis_mod13q1", "status": "unavailable", "message": "mocked offline", "cache_hit": False, "fetched_at": "x"},
        }

    monkeypatch.setattr("app.services.get_climate_shift", fake_climate_shift)
    monkeypatch.setattr("app.services.get_soil_profile", fake_soil_profile)
    monkeypatch.setattr("app.services.get_ndvi_summary", fake_ndvi_summary)

    resp = client.post(
        "/farm/analyze",
        json={
            "location": {"lat": 31.42, "lon": 73.08},
            "current_crops": ["wheat"],
            "include_stress_test": False,
            "top_n": 3,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["climate"] is None
    assert body["soil"]["status"] == "unavailable"
    assert body["ndvi"]["status"] == "unavailable"
    assert body["stress_test"] is None
    assert len(body["rotations"]["top"]) == 3
    assert len(body["warnings"]) == 3  # climate, soil, ndvi all flagged


def test_demo_mode_requires_prebuilt_file_when_missing(monkeypatch):
    monkeypatch.setattr("app.routers.climate.load_demo_analysis", lambda: None)
    resp = client.get("/climate", params={"lat": 1, "lon": 1, "demo": True})
    assert resp.status_code == 503
