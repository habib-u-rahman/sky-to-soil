import datetime as dt

import pytest

from app.advisor.facts import (
    assemble_facts,
    compute_crop_climate_detail,
    find_rotation_entry,
    find_stress_entry,
    resolve_from_demo,
)
from app.core.demo import load_demo_analysis
from app.data.crop_repo import crops_by_id
from app.science.climatology import build_doy_climatology


def _synthetic_climatology():
    params = ["T2M_MAX", "T2M_MIN", "T2M", "PRECTOTCORR", "GWETROOT", "ALLSKY_SFC_SW_DWN", "RH2M", "WS2M"]
    series = {p: {} for p in params}
    for year in range(2015, 2020):
        date = dt.date(year, 1, 1)
        end = dt.date(year, 12, 31)
        while date <= end:
            key = date.strftime("%Y%m%d")
            in_kharif = 5 <= date.month <= 10
            series["T2M_MAX"][key] = 40.0 if in_kharif else 20.0
            series["T2M_MIN"][key] = 26.0 if in_kharif else 6.0
            series["T2M"][key] = 33.0 if in_kharif else 13.0
            series["PRECTOTCORR"][key] = 1.0 if in_kharif else 0.2
            series["GWETROOT"][key] = 0.3 if in_kharif else 0.2
            series["ALLSKY_SFC_SW_DWN"][key] = 22.0
            series["RH2M"][key] = 50.0
            series["WS2M"][key] = 1.5
            date += dt.timedelta(days=1)
    return build_doy_climatology(series)


def test_compute_crop_climate_detail_with_climatology():
    wheat = crops_by_id()["wheat"]
    detail = compute_crop_climate_detail(wheat, _synthetic_climatology(), lat=31.42)
    assert detail["data_available"] is True
    assert detail["water_deficit_mm"] >= 0
    assert detail["heat_stress_days"] >= 0
    assert detail["critical_temp_c"] == wheat["critical_temp_c"]


def test_compute_crop_climate_detail_without_climatology():
    wheat = crops_by_id()["wheat"]
    detail = compute_crop_climate_detail(wheat, None, lat=31.42)
    assert detail == {"data_available": False}


def test_find_rotation_entry_top_and_pareto():
    rotations_block = {
        "top": [{"rotation": {"Y1_kharif": "cotton"}, "base_score_0_100": 80}],
        "pareto_optimal": [{"rotation": {"Y1_kharif": "maize"}, "base_score_0_100": 70}],
    }
    assert find_rotation_entry(rotations_block, "top_0")["rotation"]["Y1_kharif"] == "cotton"
    assert find_rotation_entry(rotations_block, "pareto_0")["rotation"]["Y1_kharif"] == "maize"


def test_find_rotation_entry_out_of_range_raises():
    rotations_block = {"top": [{"rotation": {}}], "pareto_optimal": []}
    with pytest.raises(ValueError):
        find_rotation_entry(rotations_block, "top_5")


def test_find_rotation_entry_bad_format_raises():
    rotations_block = {"top": [], "pareto_optimal": []}
    with pytest.raises(ValueError):
        find_rotation_entry(rotations_block, "bogus")


def test_find_stress_entry_matches_by_rotation_plan():
    plan = {"Y1_kharif": "cotton", "Y1_rabi": None, "Y2_kharif": None, "Y2_rabi": None}
    stress_block = {"results": [{"rotation": plan, "resilience_score_0_100": 90}]}
    assert find_stress_entry(stress_block, plan)["resilience_score_0_100"] == 90


def test_find_stress_entry_returns_none_when_no_match_or_missing():
    plan = {"Y1_kharif": "cotton"}
    assert find_stress_entry(None, plan) is None
    assert find_stress_entry({"results": []}, plan) is None


def test_assemble_facts_shape():
    bundle = {
        "location": {"lat": 31.42, "lon": 73.08},
        "current_crops": ["wheat", "cotton"],
        "rotation_entry": {
            "rotation": {"Y1_kharif": None, "Y1_rabi": "wheat", "Y2_kharif": None, "Y2_rabi": "wheat"},
            "sub_scores": {"water_fit": 40.5, "heat_risk": 80.0, "soil_health": 31.6, "soil_suitability": 65.0},
            "base_score_0_100": 54.3,
            "priority_weighted_score_0_100": 57.6,
            "reasons": ["ok"],
            "warnings": ["needs irrigation"],
        },
        "stress_entry": None,
        "climate_block": None,
        "soil_layers": None,
        "per_crop_detail": {"wheat": {"data_available": False}},
        "data_sources": [{"source": "nasa_power", "status": "unavailable"}],
    }
    facts = assemble_facts(bundle)
    assert facts["rotation_crops"] == {"Y1_rabi": "Wheat (bread wheat)", "Y2_rabi": "Wheat (bread wheat)"}
    assert facts["per_crop"]["wheat"]["name"] == "Wheat (bread wheat)"
    assert facts["rotation_score"]["base_score_0_100"] == 54.3
    assert facts["stress_test"] == {"data_available": False}
    assert facts["soil"] == {"data_available": False}
    assert facts["climate_shift"] == {"data_available": False}


def test_resolve_from_demo_offline_using_frozen_demo_file():
    demo_data = load_demo_analysis()
    assert demo_data is not None, "run `python -m app.scripts.build_demo` before running this test"

    bundle = resolve_from_demo(demo_data, "top_0", ["wheat", "cotton"])
    facts = assemble_facts(bundle)
    assert facts["rotation_crops"]
    assert facts["rotation_score"]["base_score_0_100"] == demo_data["rotations"]["top"][0]["base_score_0_100"]
    for cid in bundle["per_crop_detail"]:
        assert bundle["per_crop_detail"][cid].get("data_available") in (True, False)
