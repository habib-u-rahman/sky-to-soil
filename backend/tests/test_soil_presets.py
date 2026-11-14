from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

EXPECTED_TEXTURES = {"sand", "sandy_loam", "loam", "silt_loam", "clay_loam", "clay"}


def test_soil_presets_returns_all_six_textures_with_a_source():
    resp = client.get("/soil/presets")
    assert resp.status_code == 200
    body = resp.json()
    textures = {p["texture"] for p in body["presets"]}
    assert textures == EXPECTED_TEXTURES
    assert body["source"]["status"] == "ok"
    assert body["source"]["message"]


def test_soil_presets_values_are_physically_plausible():
    resp = client.get("/soil/presets")
    for preset in resp.json()["presets"]:
        assert 0 <= preset["clay_pct"] <= 100
        assert 0 <= preset["sand_pct"] <= 100
        assert 0 <= preset["silt_pct"] <= 100
        assert 3 <= preset["phh2o"] <= 10
        assert preset["soc_g_kg"] > 0
        assert preset["cec_cmol_kg"] > 0
