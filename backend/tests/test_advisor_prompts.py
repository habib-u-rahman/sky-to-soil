"""Tests for the presentation-only cleanup in app.advisor.prompts: KB
entries and data-source ids must be rendered as human-readable names in
the prompt, without mutating the original facts/kb objects used elsewhere
(e.g. by app.advisor.verify)."""

from app.advisor.prompts import DATA_SOURCE_DISPLAY_NAMES, _facts_for_prompt, _kb_for_prompt


def test_kb_for_prompt_strips_internal_id():
    kb_entries = [{"id": "residue_som_01", "source": "FAO guidance on crop residues", "statement": "..."}]
    rendered = _kb_for_prompt(kb_entries)
    assert rendered == [{"source": "FAO guidance on crop residues", "statement": "..."}]
    assert "id" not in rendered[0]


def test_facts_for_prompt_renders_human_readable_data_source_names():
    facts = {
        "location": {"lat": 1, "lon": 2},
        "data_sources": [{"source": "nasa_power", "status": "ok"}, {"source": "isric_soilgrids", "status": "unavailable"}],
    }
    rendered = _facts_for_prompt(facts)
    sources = [d["source"] for d in rendered["data_sources"]]
    assert sources == ["NASA POWER", "ISRIC SoilGrids"]
    # original object is untouched -- verify_output still matches against raw ids
    assert facts["data_sources"][0]["source"] == "nasa_power"


def test_facts_for_prompt_is_a_noop_without_data_sources():
    facts = {"location": {"lat": 1, "lon": 2}}
    assert _facts_for_prompt(facts) is facts


def test_every_raw_data_source_id_has_a_display_name():
    from app.advisor.verify import RAW_DATA_SOURCE_IDS

    for source_id in RAW_DATA_SOURCE_IDS:
        assert source_id in DATA_SOURCE_DISPLAY_NAMES, f"{source_id} has no display name mapping"
