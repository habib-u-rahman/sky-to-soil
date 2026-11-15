"""Tests for the rule-based (no-LLM) output verifier in app.advisor.verify."""

from app.advisor.verify import verify_output

FACTS = {
    "location": {"lat": 31.42, "lon": 73.08},
    "current_crops": ["wheat", "cotton"],
    "rotation_crops": {"Y1_rabi": "Wheat (bread wheat)", "Y2_rabi": "Wheat (bread wheat)"},
    "per_crop": {
        "wheat": {
            "name": "Wheat (bread wheat)",
            "slot": "Y1_rabi",
            "family": "Poaceae",
            "n_fixing": False,
            "residue_contribution": "medium",
            "data_available": True,
            "water_deficit_mm": 206.8,
            "heat_stress_days": 0,
        }
    },
    "rotation_score": {
        "base_score_0_100": 54.3,
        "priority_weighted_score_0_100": 57.6,
        "sub_scores": {"water_fit": 40.5, "heat_risk": 80.0, "soil_health": 31.6, "soil_suitability": 65.0},
        "reasons": ["A workable rotation."],
        "warnings": ["This rotation likely needs significant supplemental irrigation."],
    },
    "stress_test": {"data_available": False},
    "soil": {"data_available": False},
    "climate_shift": {"data_available": True, "delta_tmax_c": -0.849, "delta_tmin_c": -0.225},
    "data_sources": [
        {"source": "nasa_power", "status": "ok"},
        {"source": "isric_soilgrids", "status": "unavailable"},
        {"source": "sky_to_soil_rotation_optimizer", "status": "ok"},
    ],
}

KB_USED = [
    {"id": "fao56_02", "source": "FAO-56", "statement": "..."},
    {"id": "residue_som_01", "source": "FAO guidance on crop residues and soil organic matter", "statement": "..."},
]

GOOD_TEXT = (
    "This rotation grows Wheat (bread wheat) in both rabi seasons, matching your current wheat and cotton. "
    "The base score is 54.3 out of 100. Expect a water deficit of about 206.8 mm, so plan supplemental "
    "irrigation. Keep crop residue in the field to build soil organic matter (FAO-56). "
    "Confirm this plan with your local extension officer before making changes."
)
GOOD_TECH_NOTE = "Base score 54.3, water_fit 40.5. Draws on FAO-56. Confirm with a local extension officer."


def test_good_text_passes_all_checks():
    result = verify_output(GOOD_TEXT, GOOD_TECH_NOTE, FACTS, KB_USED)
    assert result["verified"] is True
    assert result["issues"] == []


def test_invented_number_is_flagged():
    text = GOOD_TEXT.replace("206.8 mm", "999.9 mm") + " Confirm with your local extension officer."
    result = verify_output(text, "", FACTS, KB_USED)
    assert result["verified"] is False
    assert any("999.9" in i for i in result["issues"])


def test_rounded_number_within_tolerance_passes():
    # 206.8 rounded to the nearest whole mm (207) must still match.
    text = "Water deficit is about 207 mm. Confirm with your local extension officer."
    result = verify_output(text, "", FACTS, KB_USED)
    assert result["verified"] is True


def test_structural_small_numbers_and_scale_denominator_allowed():
    text = (
        "Here are 3 tips for this 2-year rotation, scored 54/100. "
        "Confirm with your local extension officer."
    )
    result = verify_output(text, "", FACTS, KB_USED)
    assert result["verified"] is True


def test_disallowed_crop_mention_is_flagged():
    text = (
        "This rotation grows Wheat (bread wheat) and Rice (paddy, transplanted) together. "
        "Confirm with your local extension officer."
    )
    result = verify_output(text, "", FACTS, KB_USED)
    assert result["verified"] is False
    assert any("Rice" in i for i in result["issues"])


def test_uncited_source_is_flagged():
    text = (
        "Wheat suits this plan per ISRIC SoilGrids analysis. Confirm with your local extension officer."
    )
    result = verify_output(text, "", FACTS, KB_USED)
    assert result["verified"] is False
    assert any("isric_soilgrids" in i for i in result["issues"])


def test_guarantee_language_is_flagged():
    text = "This rotation is guaranteed to increase your profit. Confirm with your local extension officer."
    result = verify_output(text, "", FACTS, KB_USED)
    assert result["verified"] is False
    assert any("guarantee" in i for i in result["issues"])


def test_missing_extension_officer_line_is_flagged():
    text = "This rotation grows Wheat (bread wheat) and scores 54 out of 100."
    result = verify_output(text, "", FACTS, KB_USED)
    assert result["verified"] is False
    assert any("extension officer" in i for i in result["issues"])


def test_urdu_text_passes_with_urdu_digits_and_crop_names():
    text = (
        "یہ ترتیب گندم پر مشتمل ہے اور اس کا بیس سکور ۵۴ ہے۔ "
        "پانی کی کمی تقریباً ۲۰۷ ملی میٹر ہے۔ "
        "مقامی زرعی توسیعی اہلکار سے تصدیق کریں۔"
    )
    result = verify_output(text, "", FACTS, KB_USED)
    assert result["verified"] is True, result["issues"]


def test_urdu_guarantee_language_is_flagged():
    text = "اس ترتیب سے یقینی طور پر زیادہ منافع ہوگا۔ مقامی زرعی توسیعی اہلکار سے تصدیق کریں۔"
    result = verify_output(text, "", FACTS, KB_USED)
    assert result["verified"] is False


def test_farmer_text_containing_the_word_kb_is_flagged():
    text = GOOD_TEXT + " KB basis: FAO-56."
    result = verify_output(text, "", FACTS, KB_USED)
    assert result["verified"] is False
    assert any("KB" in i for i in result["issues"])


def test_farmer_text_containing_internal_kb_id_is_flagged():
    text = GOOD_TEXT.replace("(FAO-56)", "(residue_som_01)")
    result = verify_output(text, "", FACTS, KB_USED)
    assert result["verified"] is False
    assert any("residue_som_01" in i for i in result["issues"])


def test_farmer_text_containing_raw_data_source_id_is_flagged():
    text = GOOD_TEXT + " Source: nasa_power."
    result = verify_output(text, "", FACTS, KB_USED)
    assert result["verified"] is False
    assert any("nasa_power" in i for i in result["issues"])


def test_technical_note_may_still_say_kb_basis():
    # The word "KB" and precise source labels are fine in technical_note --
    # that section is explicitly for an extension officer, not the farmer.
    result = verify_output(GOOD_TEXT, "KB basis: FAO-56. Confirm with a local extension officer.", FACTS, KB_USED)
    assert result["verified"] is True, result["issues"]
