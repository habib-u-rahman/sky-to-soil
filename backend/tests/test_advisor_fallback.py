"""The fallback template is the safety net the AI Agronomist falls back on
when the LLM write+rewrite path still fails verification -- it MUST always
pass verify_output on its own, for every language, since it's also what
powers demo mode and any Groq outage."""

from app.advisor.fallback_template import build_fallback_chat, build_fallback_explain, select_fallback_kb
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

# A legume-containing rotation, to exercise the "legume" branch of
# select_fallback_kb and the Urdu crop-name allow-list for a second crop.
FACTS_WITH_LEGUME = {
    **FACTS,
    "rotation_crops": {"Y1_kharif": "Mungbean (green gram)", "Y1_rabi": "Wheat (bread wheat)"},
    "per_crop": {
        **FACTS["per_crop"],
        "mungbean": {
            "name": "Mungbean (green gram)",
            "slot": "Y1_kharif",
            "family": "Fabaceae",
            "n_fixing": True,
            "residue_contribution": "low",
            "data_available": True,
            "water_deficit_mm": 40.0,
            "heat_stress_days": 2,
        },
    },
}


def test_select_fallback_kb_returns_up_to_4_entries():
    kb = select_fallback_kb(FACTS)
    assert 1 <= len(kb) <= 4
    assert all({"id", "source", "statement"} <= set(e) for e in kb)


def test_select_fallback_kb_prioritizes_legume_when_present():
    kb = select_fallback_kb(FACTS_WITH_LEGUME)
    sources = [e["source"] for e in kb]
    assert "legume nitrogen fixation" in sources


def test_fallback_explain_passes_verify_in_english():
    text, tech_note, kb_used = build_fallback_explain(FACTS, FACTS["current_crops"], "en")
    result = verify_output(text, tech_note, FACTS, kb_used)
    assert result["verified"] is True, result["issues"]


def test_fallback_explain_passes_verify_in_urdu():
    text, tech_note, kb_used = build_fallback_explain(FACTS, FACTS["current_crops"], "ur")
    result = verify_output(text, tech_note, FACTS, kb_used)
    assert result["verified"] is True, result["issues"]


def test_fallback_explain_with_legume_passes_verify_both_languages():
    for language in ("en", "ur"):
        text, tech_note, kb_used = build_fallback_explain(
            FACTS_WITH_LEGUME, list(FACTS_WITH_LEGUME["current_crops"]), language
        )
        result = verify_output(text, tech_note, FACTS_WITH_LEGUME, kb_used)
        assert result["verified"] is True, (language, result["issues"])


def test_fallback_chat_passes_verify_and_reports_unanswerable():
    for language in ("en", "ur"):
        answer, answerable, kb_used = build_fallback_chat(FACTS, "What will wheat sell for next year?", language)
        result = verify_output(answer, "", FACTS, kb_used)
        assert result["verified"] is True, (language, result["issues"])
        assert answerable is False
