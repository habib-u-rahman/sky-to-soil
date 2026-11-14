from app.science.soil_suitability import (
    classify_texture,
    crop_soil_suitability,
    score_ph,
    score_texture,
    weighted_profile_mean,
)

WHEAT = {"ph_min": 6.0, "ph_max": 7.5, "texture_preference": ["loam", "clay_loam", "silt_loam"]}


def test_classify_texture_clay_dominant():
    assert classify_texture(clay_pct=40, sand_pct=20, silt_pct=40) == "clay"


def test_classify_texture_sandy_loam():
    assert classify_texture(clay_pct=10, sand_pct=60, silt_pct=30) == "sandy_loam"


def test_classify_texture_none_when_no_data():
    assert classify_texture(None, None, None) is None


def test_score_ph_within_range_is_100():
    assert score_ph(7.0, WHEAT["ph_min"], WHEAT["ph_max"]) == 100.0


def test_score_ph_outside_range_decreases_with_distance():
    near = score_ph(5.8, WHEAT["ph_min"], WHEAT["ph_max"])  # 0.2 below ph_min
    far = score_ph(4.0, WHEAT["ph_min"], WHEAT["ph_max"])  # 2.0 below ph_min
    assert near > far
    assert near < 100.0


def test_score_ph_none_returns_default():
    from app.science.soil_suitability import DEFAULT_SUITABILITY_SCORE

    assert score_ph(None, 6.0, 7.5) == DEFAULT_SUITABILITY_SCORE


def test_score_texture_match_vs_mismatch():
    assert score_texture("loam", WHEAT["texture_preference"]) == 100.0
    assert score_texture("sandy_loam", WHEAT["texture_preference"]) < 100.0


def test_weighted_profile_mean_weights_by_depth_thickness():
    layers = [
        {"depth": "0-5cm", "phh2o": 6.0},
        {"depth": "5-15cm", "phh2o": 7.0},
        {"depth": "15-30cm", "phh2o": 8.0},
    ]
    # weights 5:10:15 -> (6*5 + 7*10 + 8*15) / 30 = 7.33
    result = weighted_profile_mean(layers, "phh2o")
    assert abs(result - 7.33) < 0.01


def test_crop_soil_suitability_no_layers_returns_default():
    result = crop_soil_suitability(WHEAT, None)
    assert result["used_defaults"] is True
    assert result["score"] == 70.0


def test_crop_soil_suitability_good_match_scores_high():
    layers = [
        {"depth": "0-5cm", "phh2o": 6.8, "clay_pct": 20, "sand_pct": 30, "silt_pct": 50},
        {"depth": "5-15cm", "phh2o": 6.8, "clay_pct": 20, "sand_pct": 30, "silt_pct": 50},
        {"depth": "15-30cm", "phh2o": 6.8, "clay_pct": 20, "sand_pct": 30, "silt_pct": 50},
    ]
    result = crop_soil_suitability(WHEAT, layers)
    assert result["score"] >= 70.0
