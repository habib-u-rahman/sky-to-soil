"""Deterministic, LLM-free fallback. Used only when the LLM write+rewrite
path still fails verification after one rewrite -- guarantees the advisor
always returns *something* grounded strictly in `facts`, with no network
dependency, so it also powers demo mode and any Groq outage.
"""

from __future__ import annotations

from app.advisor.kb import load_kb
from app.data.crop_repo import crops_by_id

EXT_OFFICER_LINE = {
    "en": "As always, confirm this plan with your local extension officer before making changes.",
    "ur": "ہمیشہ کی طرح، کوئی تبدیلی کرنے سے پہلے اپنے مقامی زرعی توسیعی اہلکار سے اس منصوبے کی تصدیق کریں۔",
}

NO_GUARANTEE_LINE = {
    "en": "This is guidance to consider, not a guarantee of yield or income.",
    "ur": "یہ غور کرنے کے لیے رہنمائی ہے، پیداوار یا آمدنی کی ضمانت نہیں۔",
}


def _kb_by_source(source: str) -> dict | None:
    for entry in load_kb():
        if entry["source"] == source:
            return entry
    return None


def select_fallback_kb(facts: dict) -> list[dict]:
    """Deterministically picks up to 4 KB entries most relevant to this
    rotation's sub-scores, in a fixed priority order."""
    sub_scores = facts.get("rotation_score", {}).get("sub_scores", {})
    legumes = [c for c, meta in facts.get("per_crop", {}).items() if meta.get("n_fixing")]

    priority: list[str] = []
    if sub_scores.get("water_fit", 100) < 75:
        priority.append("water-saving practices")
    if sub_scores.get("heat_risk", 100) < 75:
        priority.append("heat stress at flowering")
    if legumes:
        priority.append("legume nitrogen fixation")
    priority.append("crop diversity and pest breaks")
    priority.append("crop residue and soil organic matter")
    priority.append("FAO conservation agriculture")

    picked, seen = [], set()
    for source in priority:
        entry = _kb_by_source(source)
        if entry and entry["source"] not in seen:
            picked.append(entry)
            seen.add(entry["source"])
        if len(picked) == 4:
            break
    return picked


def _rotation_list_en(rotation_crops: dict) -> str:
    return ", ".join(f"{slot.replace('_', ' ')}: {name}" for slot, name in rotation_crops.items()) or "no crops (fallow)"


def _rotation_list_ur(rotation_crops: dict) -> str:
    slot_names_ur = {"Y1_kharif": "سال 1 خریف", "Y1_rabi": "سال 1 ربیع", "Y2_kharif": "سال 2 خریف", "Y2_rabi": "سال 2 ربیع"}
    return "، ".join(f"{slot_names_ur.get(slot, slot)}: {name}" for slot, name in rotation_crops.items()) or "کوئی فصل نہیں (کھیت خالی)"


def _display_names(crop_ids: list[str]) -> list[str]:
    lookup = crops_by_id()
    return [lookup[c]["name"] if c in lookup else c for c in crop_ids]


def build_fallback_explain(facts: dict, current_crops: list[str], language: str) -> tuple[str, str, list[dict]]:
    current_crops = _display_names(current_crops)
    kb_used = select_fallback_kb(facts)
    sub_scores = facts["rotation_score"]["sub_scores"]
    base_score = facts["rotation_score"]["base_score_0_100"]
    weighted_score = facts["rotation_score"]["priority_weighted_score_0_100"]
    warnings = facts["rotation_score"].get("warnings", [])
    climate = facts.get("climate_shift", {})

    tips_en = [f"{e['statement']} (source: {e['source']})" for e in kb_used[:3]]
    tips_ur_source_label = [e["source"] for e in kb_used[:3]]

    if language == "ur":
        rotation_line = _rotation_list_ur(facts["rotation_crops"])
        lines = [
            f"آپ کی موجودہ فصلیں: {', '.join(current_crops) or 'کوئی نہیں بتائی گئیں'}۔",
            f"تجویز کردہ دو سالہ ترتیب: {rotation_line}۔",
            f"مجموعی سکور {base_score:.0f}/100 اور آپ کی ترجیحات کے مطابق وزنی سکور {weighted_score:.0f}/100 ہے۔",
        ]
        if climate.get("data_available"):
            lines.append(
                f"حالیہ دورانیے میں زیادہ سے زیادہ درجہ حرارت بنیادی دورانیے کے مقابلے میں تقریباً {climate.get('delta_tmax_c', 0):.1f}°C "
                f"تبدیل ہوا ہے۔"
            )
        else:
            lines.append("اس مقام کے لیے موسمیاتی رجحان کا ڈیٹا دستیاب نہیں تھا۔")
        if warnings:
            lines.append("دھیان رہے: " + "؛ ".join(warnings))
        lines.append("تین عملی مشورے:")
        for i, source in enumerate(tips_ur_source_label, start=1):
            lines.append(f"{i}. ({source})")
        lines.append(NO_GUARANTEE_LINE["ur"])
        lines.append(EXT_OFFICER_LINE["ur"])
        farmer_text = "\n".join(lines)
    else:
        rotation_line = _rotation_list_en(facts["rotation_crops"])
        lines = [
            f"Your current crops: {', '.join(current_crops) or 'none given'}.",
            f"Recommended 2-year sequence: {rotation_line}.",
            f"Overall score {base_score:.0f}/100, and {weighted_score:.0f}/100 weighted to your stated priorities.",
        ]
        if climate.get("data_available"):
            lines.append(
                f"In the recent period, mean max temperature has shifted by about {climate.get('delta_tmax_c', 0):.1f}°C "
                f"versus the baseline period."
            )
        else:
            lines.append("Climate trend data wasn't available for this location.")
        if warnings:
            lines.append("Watch out for: " + "; ".join(warnings))
        lines.append("Three practical tips:")
        for i, tip in enumerate(tips_en, start=1):
            lines.append(f"{i}. {tip}")
        lines.append(NO_GUARANTEE_LINE["en"])
        lines.append(EXT_OFFICER_LINE["en"])
        farmer_text = "\n".join(lines)

    technical_note = (
        f"Rotation sub-scores: water_fit={sub_scores['water_fit']:.0f}, heat_risk={sub_scores['heat_risk']:.0f}, "
        f"soil_health={sub_scores['soil_health']:.0f}, soil_suitability={sub_scores['soil_suitability']:.0f}. "
        f"Base score {base_score:.0f}/100. KB basis: {', '.join(e['source'] for e in kb_used)}. "
        f"Template fallback (automated rewrite did not pass fact-check). {EXT_OFFICER_LINE['en']}"
    )
    return farmer_text, technical_note, kb_used


def build_fallback_chat(facts: dict, question: str, language: str) -> tuple[str, bool, list[dict]]:
    kb_used = select_fallback_kb(facts)
    if language == "ur":
        answer = (
            "میں اس سوال کا تصدیق شدہ جواب اس فارم کے حقائق سے نہیں دے سکا۔ "
            "براہ کرم بارش، درجہ حرارت کی تبدیلی، مٹی، یا تجویز کردہ فصل کی ترتیب کے بارے میں پوچھیں۔ "
            + EXT_OFFICER_LINE["ur"]
        )
    else:
        answer = (
            "I couldn't verify a confident answer to that from this farm's facts. "
            "Please ask about rainfall, temperature shifts, soil, or the recommended rotation for this farm. "
            + EXT_OFFICER_LINE["en"]
        )
    return answer, False, kb_used
