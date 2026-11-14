"""Tests for the agronomy knowledge base loader and TF-IDF retrieval."""

from app.advisor.kb import build_retrieval_query, load_kb, retrieve


def test_kb_has_25_to_40_entries_each_with_source_and_statement():
    kb = load_kb()
    assert 25 <= len(kb) <= 40
    for entry in kb:
        assert entry["id"]
        assert entry["source"]
        assert entry["statement"]


def test_kb_covers_all_required_topic_categories():
    required = {
        "FAO-56",
        "FAO conservation agriculture",
        "legume nitrogen fixation",
        "crop residue and soil organic matter",
        "crop diversity and pest breaks",
        "heat stress at flowering",
        "water-saving practices",
    }
    sources = {entry["source"] for entry in load_kb()}
    assert required.issubset(sources)


def test_retrieve_returns_requested_top_k():
    results = retrieve("legume nitrogen fixation nitrogen rhizobia", top_k=4)
    assert len(results) == 4


def test_retrieve_ranks_relevant_topic_first():
    results = retrieve("legume nitrogen fixation rhizobia nodules", top_k=3)
    assert results[0]["source"] == "legume nitrogen fixation"


def test_retrieve_heat_stress_query_returns_heat_topic():
    results = retrieve("heat stress flowering critical temperature", top_k=3)
    sources = {r["source"] for r in results}
    assert "heat stress at flowering" in sources


def test_retrieve_empty_query_still_returns_entries():
    results = retrieve("", top_k=5)
    assert len(results) == 5


def test_build_retrieval_query_includes_crop_names_and_question():
    facts = {
        "rotation_crops": {"Y1_rabi": "Wheat (bread wheat)"},
        "current_crops": ["cotton"],
        "rotation_score": {"sub_scores": {"water_fit": 40, "heat_risk": 90, "soil_health": 80}},
        "per_crop": {"wheat": {"n_fixing": False}},
    }
    query = build_retrieval_query(facts, question="How much water does it need?")
    assert "Wheat (bread wheat)" in query
    assert "cotton" in query
    assert "How much water does it need?" in query
    assert "water saving" in query  # water_fit below threshold triggers this theme
