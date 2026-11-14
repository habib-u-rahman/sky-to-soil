import datetime as dt

from app.science.climatology import build_doy_climatology
from app.science.rotation_engine import (
    SLOTS,
    _generate_candidate_slot_assignments,
    pareto_optimal_set,
    score_all_rotations,
    stress_test_rotations,
)


def _faisalabad_like_climatology():
    """Build a plausible day-of-year climatology: hot wet-ish kharif
    (May-Oct), cooler dry rabi (Nov-Apr) -- roughly Punjab-like."""
    params = ["T2M_MAX", "T2M_MIN", "T2M", "PRECTOTCORR", "GWETROOT", "ALLSKY_SFC_SW_DWN", "RH2M", "WS2M"]
    series = {p: {} for p in params}
    for year in range(2015, 2020):
        date = dt.date(year, 1, 1)
        end = dt.date(year, 12, 31)
        while date <= end:
            key = date.strftime("%Y%m%d")
            in_kharif = 5 <= date.month <= 10
            series["T2M_MAX"][key] = 38.0 if in_kharif else 22.0
            series["T2M_MIN"][key] = 26.0 if in_kharif else 8.0
            series["T2M"][key] = 32.0 if in_kharif else 15.0
            series["PRECTOTCORR"][key] = 4.0 if in_kharif else 0.3
            series["GWETROOT"][key] = 0.4 if in_kharif else 0.25
            series["ALLSKY_SFC_SW_DWN"][key] = 22.0
            series["RH2M"][key] = 55.0
            series["WS2M"][key] = 1.5
            date += dt.timedelta(days=1)
    return build_doy_climatology(series)


DEFAULT_PRIORITIES = {
    "save_water": 0.25,
    "build_soil": 0.25,
    "lower_climate_risk": 0.25,
    "stay_close_to_current": 0.25,
    "income_proxy": None,
}


def test_generate_candidates_is_nonempty():
    candidates = _generate_candidate_slot_assignments()
    assert len(candidates) > 1000


def test_sugarcane_block_candidates_always_pair_adjacent_slots():
    candidates = _generate_candidate_slot_assignments()
    sugarcane_candidates = [c for c in candidates if "sugarcane" in c.values()]
    assert sugarcane_candidates  # at least some exist

    for cand in sugarcane_candidates:
        sugarcane_slots = [s for s in SLOTS if cand[s] == "sugarcane"]
        assert len(sugarcane_slots) == 2
        idx = [SLOTS.index(s) for s in sugarcane_slots]
        assert abs(idx[0] - idx[1]) == 1  # the two sugarcane slots are adjacent


def test_score_all_rotations_returns_valid_score_ranges():
    clim = _faisalabad_like_climatology()
    result = score_all_rotations(
        climatology=clim,
        soil_layers=None,
        priorities=DEFAULT_PRIORITIES,
        current_crops=["wheat", "cotton"],
        lat=31.42,
        top_n=10,
    )
    assert result["candidates_evaluated"] > 1000
    assert len(result["top"]) == 10

    for rotation in result["top"]:
        for key in ("water_fit", "heat_risk", "soil_health", "soil_suitability"):
            assert 0 <= rotation["sub_scores"][key] <= 100
        assert 0 <= rotation["base_score_0_100"] <= 100
        assert 0 <= rotation["priority_weighted_score_0_100"] <= 100

    # top list should be sorted by priority_weighted_score descending
    scores = [r["priority_weighted_score_0_100"] for r in result["top"]]
    assert scores == sorted(scores, reverse=True)


def test_score_all_rotations_works_without_climate_or_soil_data():
    result = score_all_rotations(
        climatology=None,
        soil_layers=None,
        priorities=DEFAULT_PRIORITIES,
        current_crops=[],
        lat=31.42,
        top_n=5,
    )
    assert len(result["top"]) == 5
    for rotation in result["top"]:
        for key in ("water_fit", "heat_risk", "soil_health", "soil_suitability"):
            assert 0 <= rotation["sub_scores"][key] <= 100


def test_build_soil_priority_favors_legume_heavy_rotations():
    clim = _faisalabad_like_climatology()
    soil_only_priorities = {
        "save_water": 0.0,
        "build_soil": 1.0,
        "lower_climate_risk": 0.0,
        "stay_close_to_current": 0.0,
        "income_proxy": None,
    }
    result = score_all_rotations(
        climatology=clim, soil_layers=None, priorities=soil_only_priorities, current_crops=[], lat=31.42, top_n=5
    )
    top = result["top"][0]
    assert top["sub_scores"]["soil_health"] >= 65


def test_pareto_optimal_set_contains_no_dominated_candidate():
    clim = _faisalabad_like_climatology()
    result = score_all_rotations(
        climatology=clim, soil_layers=None, priorities=DEFAULT_PRIORITIES, current_crops=[], lat=31.42, top_n=10
    )
    front = result["pareto_optimal"]
    assert len(front) > 0

    keys = ["water_fit", "heat_risk", "soil_health", "soil_suitability"]
    for a in front:
        for b in front:
            if a is b:
                continue
            all_ge = all(b["sub_scores"][k] >= a["sub_scores"][k] for k in keys)
            any_gt = any(b["sub_scores"][k] > a["sub_scores"][k] for k in keys)
            assert not (all_ge and any_gt), "pareto front contains a dominated candidate"


def test_stress_test_resilience_scores_are_bounded():
    clim = _faisalabad_like_climatology()
    result = stress_test_rotations(
        climatology=clim,
        soil_layers=None,
        priorities=DEFAULT_PRIORITIES,
        current_crops=[],
        lat=31.42,
        delta_temp_c=1.5,
        rainfall_change_pct=-15,
        top_n=5,
    )
    assert len(result["results"]) == 5
    for r in result["results"]:
        assert 0 <= r["resilience_score_0_100"] <= 100
        assert 0 <= r["baseline_score_0_100"] <= 100
        assert 0 <= r["stressed_score_0_100"] <= 100


def test_stress_test_hotter_drier_scenario_tends_to_lower_scores():
    clim = _faisalabad_like_climatology()
    result = stress_test_rotations(
        climatology=clim,
        soil_layers=None,
        priorities=DEFAULT_PRIORITIES,
        current_crops=[],
        lat=31.42,
        delta_temp_c=1.5,
        rainfall_change_pct=-15,
        top_n=5,
    )
    # On average, a hotter/drier scenario should not improve scores.
    avg_drop = sum(r["score_drop"] for r in result["results"]) / len(result["results"])
    assert avg_drop >= -1.0  # allow tiny numerical noise, but no real improvement expected
