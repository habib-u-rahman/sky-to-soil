import datetime as dt

from app.data.crop_repo import crops_by_id
from app.science.climatology import build_doy_climatology
from app.science.rotation_engine import (
    MAX_FALLOW_SLOTS,
    SLOTS,
    _generate_candidate_slot_assignments,
    _land_use_score,
    _soil_health_score,
    pareto_optimal_set,
    score_all_rotations,
    stress_test_rotations,
)

LEGUME_IDS = {"mungbean", "chickpea", "lentil", "berseem_clover", "soybean"}
SUB_SCORE_KEYS = ("water_fit", "heat_risk", "soil_health", "soil_suitability", "land_use")


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
        for key in SUB_SCORE_KEYS:
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
        for key in SUB_SCORE_KEYS:
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

    keys = list(SUB_SCORE_KEYS)
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


# ---------------------------------------------------------------------------
# Realism fixes: fallow cap, land-use penalty, legume/diversity soil health,
# soft (not filtering) "stay close to current crops" preference.
# ---------------------------------------------------------------------------


def test_no_candidate_has_more_than_one_fallow_slot():
    candidates = _generate_candidate_slot_assignments()
    for cand in candidates:
        fallow_count = sum(1 for v in cand.values() if v is None)
        assert fallow_count <= MAX_FALLOW_SLOTS


def test_land_use_score_penalizes_fallow_slots():
    all_cropped = {"Y1_kharif": "cotton", "Y1_rabi": "wheat", "Y2_kharif": "cotton", "Y2_rabi": "wheat"}
    one_fallow = {"Y1_kharif": "cotton", "Y1_rabi": "wheat", "Y2_kharif": None, "Y2_rabi": "wheat"}
    assert _land_use_score(one_fallow) < _land_use_score(all_cropped)
    # A fallow slot contributes exactly 0, not some neutral/discounted value.
    two_crops_two_fallow = {"Y1_kharif": "cotton", "Y1_rabi": "wheat", "Y2_kharif": None, "Y2_rabi": None}
    from app.data.crop_repo import INCOME_PROXY

    expected = round((INCOME_PROXY["cotton"] + INCOME_PROXY["wheat"]) / 4, 1)
    assert _land_use_score(two_crops_two_fallow) == expected


def test_fallow_rotation_does_not_outscore_realistic_punjab_rotations():
    """A real cotton-wheat double-crop must not be beaten by a mostly-fallow
    rotation just because fallow has no water/heat exposure to average."""
    clim = _faisalabad_like_climatology()
    result = score_all_rotations(
        climatology=clim,
        soil_layers=None,
        priorities=DEFAULT_PRIORITIES,
        current_crops=["wheat", "cotton"],
        lat=31.42,
        top_n=10,
    )
    top_rotations = [r["rotation"] for r in result["top"]]
    fallow_counts = [sum(1 for v in rot.values() if v is None) for rot in top_rotations]
    # At least the #1 rotation should be a real, fully (or near-fully)
    # cropped sequence, not a fallow-heavy one.
    assert fallow_counts[0] <= MAX_FALLOW_SLOTS
    # No rotation anywhere in the top 10 should have been generated with
    # more than the cap allows (belt-and-suspenders on the generator fix).
    assert all(c <= MAX_FALLOW_SLOTS for c in fallow_counts)


def _meta_for(crop_id: str) -> dict:
    crop = crops_by_id()[crop_id]
    return {
        "name": crop["name"],
        "family": crop["family"],
        "n_fixing": crop["n_fixing"],
        "residue_contribution": crop["residue_contribution"],
        "rooting_depth_m": crop["rooting_depth_m"],
    }


def test_legumes_and_diversity_raise_soil_health():
    cache = {cid: _meta_for(cid) for cid in ["wheat", "cotton", "mungbean", "chickpea"]}
    cereal_repeat = {"Y1_kharif": "cotton", "Y1_rabi": "wheat", "Y2_kharif": "cotton", "Y2_rabi": "wheat"}
    legume_diverse = {"Y1_kharif": "cotton", "Y1_rabi": "wheat", "Y2_kharif": "mungbean", "Y2_rabi": "chickpea"}

    cereal_score = _soil_health_score(cereal_repeat, cache)["score"]
    legume_score = _soil_health_score(legume_diverse, cache)["score"]
    assert legume_score > cereal_score + 10  # clearly higher, not a rounding-noise difference


def test_cereal_cereal_repeat_lowers_soil_health_vs_mixed_family():
    cache = {cid: _meta_for(cid) for cid in ["wheat", "maize", "cotton"]}
    # wheat and maize are both Poaceae (cereals) -- repeating the same
    # family both years should score lower than breaking it with cotton.
    cereal_cereal = {"Y1_kharif": "maize", "Y1_rabi": "wheat", "Y2_kharif": "maize", "Y2_rabi": "wheat"}
    broken_family = {"Y1_kharif": "cotton", "Y1_rabi": "wheat", "Y2_kharif": "cotton", "Y2_rabi": "wheat"}

    cereal_detail = _soil_health_score(cereal_cereal, cache)
    broken_detail = _soil_health_score(broken_family, cache)
    assert cereal_detail["family_break_score"] == 0.0
    assert broken_detail["family_break_score"] > cereal_detail["family_break_score"]
    assert broken_detail["score"] > cereal_detail["score"]


def test_stay_close_to_current_is_soft_not_a_filter():
    """Even with 100% weight on 'stay close to current crops', rotations
    that use none of the farmer's current crops must still be scoreable
    and present among the full candidate set -- current_crops must narrow
    preference, not eligibility."""
    clim = _faisalabad_like_climatology()
    closeness_only_priorities = {
        "save_water": 0.0,
        "build_soil": 0.0,
        "lower_climate_risk": 0.0,
        "stay_close_to_current": 1.0,
        "income_proxy": None,
    }
    result = score_all_rotations(
        climatology=clim,
        soil_layers=None,
        priorities=closeness_only_priorities,
        current_crops=["wheat", "cotton"],
        lat=31.42,
        top_n=10,
    )
    all_rotation_crop_sets = [set(v for v in r["rotation"].values() if v) for r in result["top"]]
    # A rotation using exclusively wheat/cotton must be achievable and
    # should dominate the top list under this priority...
    assert any(crops <= {"wheat", "cotton"} for crops in all_rotation_crop_sets)
    # ...but the generator must not have been restricted to only those
    # crops: legumes and other crops still exist among all candidates.
    candidates = _generate_candidate_slot_assignments()
    assert any(LEGUME_IDS & set(v for v in cand.values() if v) for cand in candidates)


def test_top5_includes_a_legume_rotation_within_10_points_under_default_priorities():
    clim = _faisalabad_like_climatology()
    result = score_all_rotations(
        climatology=clim,
        soil_layers=None,
        priorities=DEFAULT_PRIORITIES,
        current_crops=["wheat", "cotton"],
        lat=31.42,
        top_n=10,
    )
    top = result["top"]
    top5_score = top[4]["priority_weighted_score_0_100"]

    def has_legume(rotation: dict) -> bool:
        return any(v in LEGUME_IDS for v in rotation.values() if v)

    legume_within_10pts = any(
        has_legume(r["rotation"]) and r["priority_weighted_score_0_100"] >= top5_score - 10 for r in top[:5]
    )
    assert legume_within_10pts, [
        (r["priority_weighted_score_0_100"], r["rotation"]) for r in top[:5]
    ]
