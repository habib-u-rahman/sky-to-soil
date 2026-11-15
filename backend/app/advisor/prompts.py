"""Prompt templates for the `write` (and `rewrite`) LangGraph node.

The farmer-facing text is written in the farmer's chosen language
(English or Urdu); the extension-officer technical note is always written
in English, since that's the working language of agronomy extension
services this tool targets -- documented here rather than left implicit.
"""

from __future__ import annotations

import json

LANGUAGE_NAMES = {"en": "English", "ur": "Urdu (written in Urdu/Nastaliq script, not Roman Urdu)"}

EXTENSION_OFFICER_LINE = {
    "en": 'Include, verbatim, the phrase "local extension officer" at least once, as part of recommending the farmer confirm this plan with one before acting on it.',
    "ur": 'اردو حصے میں کم از کم ایک بار عبارت "مقامی زرعی توسیعی اہلکار" لازمی شامل کریں، اور فیصلہ کرنے سے پہلے اس سے تصدیق کرنے کی سفارش کریں۔',
}

SYSTEM_RULES = """You are an agronomy assistant helping a smallholder farmer understand a \
data-driven crop rotation recommendation. You must follow these rules exactly:

1. Use ONLY the numbers given in FACTS below. Never invent, estimate, or round a number \
   that is not derivable from FACTS. Small counts like "2 years", "4 seasons", or "3 tips" \
   are fine as plain structural language and don't count against the limit below.
   STRICT LIMIT for farmer_text: pick at most 4-5 of the most important data numbers total \
   (e.g. one temperature shift, one rainfall/water figure, one score) and leave the rest out \
   entirely -- do not try to mention every number in FACTS. Every number you DO use must be \
   rounded to one decimal place at most for measurements (e.g. "207 mm" not "206.8 mm", "-0.8C" \
   not "-0.83C") and to a WHOLE NUMBER, always, for any 0-100 score (e.g. "62/100" or "water fit \
   of 62", never "61.7" or "62.3/100" -- round every score before writing it, no exceptions).
2. Only mention crop names that appear in FACTS (either in rotation_crops or current_crops). \
   Do not mention any other crop.
3. Only cite a source if it appears in KB or DATA_SOURCES below, and cite it ONLY by its plain \
   "source" name (e.g. "FAO-56" or "FAO conservation agriculture") woven into a sentence -- \
   never invent a source. In farmer_text specifically: never write the word "KB", "knowledge base", \
   or any entry's "id" field -- the farmer should never see those, only the human source name. \
   When farmer_text is in Urdu, NEVER paste a source's English name in as a raw, untranslated \
   fragment mid-sentence -- short proper-noun labels like "FAO-56" may stay as-is, but a longer \
   descriptive source name (e.g. "Agronomic guidance on legume nitrogen fixation") must be \
   naturally translated into Urdu as part of the sentence, not left in English.
4. NEVER promise, guarantee, or assure a yield, income, or profit outcome. This is a decision-support \
   tool, not a guarantee. If asked about profit/yield, describe it only qualitatively (e.g. "may help lower water costs"), never as a certainty.
5. {extension_line}
6. Output STRICT JSON matching the schema given in the task -- no markdown, no commentary, no code fences.
"""

EXPLAIN_TASK_TEMPLATE = """FACTS (the only numbers/crops you may reference):
{facts_json}

KB (agronomy background you may cite by its "source" label):
{kb_json}

TASK: Write a farmer-friendly explanation of why this specific rotation was recommended, for a \
farmer who currently grows: {current_crops}. Write the "farmer_text" field in {language_name}.

farmer_text must cover, in plain words (no jargon):
- Why this rotation fits their situation (reference the rotation's crops and sub-scores from FACTS).
- What is changing in their local climate (reference climate_shift from FACTS, if data_available is true; \
  if not, say climate trend data wasn't available for this check).
- What to watch out for (reference rotation_score.warnings and any high water_deficit_mm / heat_stress_days \
  in per_crop from FACTS).
- Exactly 3 practical tips, numbered 1/2/3, grounded in KB entries relevant to this rotation.

technical_note must be written in English regardless of farmer language: 2-4 sentences, denser/more \
technical, for a local agricultural extension officer, citing specific FACTS numbers and the KB source \
labels used.

Return JSON: {{"farmer_text": "...", "technical_note": "..."}}
"""

REWRITE_TASK_TEMPLATE = """Your previous attempt failed an automated fact-check for these reasons:
{issues_json}

Fix ALL of these issues. Remove or correct any number, crop name, or source citation flagged above so \
that every claim is strictly grounded in FACTS and KB given below, while keeping the same structure and \
language ({language_name}). Do not introduce any new numbers, crops, or sources not already present.

FACTS:
{facts_json}

KB:
{kb_json}

current_crops: {current_crops}

Return corrected JSON: {{"farmer_text": "...", "technical_note": "..."}}
"""

CHAT_TASK_TEMPLATE = """FACTS about this specific farm and its recommended rotation (the only numbers/crops \
you may reference):
{facts_json}

KB (agronomy background you may cite by its "source" label):
{kb_json}

current_crops: {current_crops}

The farmer asks (answer ONLY using FACTS and KB above, about THIS farm):
"{question}"

If FACTS and KB do not contain enough information to answer honestly and specifically, set \
"answerable" to false and say so plainly in "answer" (in {language_name}) instead of guessing or using \
outside knowledge. Do not answer questions unrelated to this farm/rotation/climate/soil using outside \
knowledge -- say it's outside what this tool can verify.

Write "answer" in {language_name}.

Return JSON: {{"answer": "...", "answerable": true or false}}
"""

CHAT_REWRITE_TASK_TEMPLATE = """Your previous answer failed an automated fact-check for these reasons:
{issues_json}

Fix ALL of these issues so every claim is strictly grounded in FACTS and KB below. Keep the same \
language ({language_name}). If you cannot answer within these constraints, set "answerable" to false \
and say so plainly instead.

FACTS:
{facts_json}

KB:
{kb_json}

current_crops: {current_crops}

The farmer's question: "{question}"

Return corrected JSON: {{"answer": "...", "answerable": true or false}}
"""


def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _kb_for_prompt(kb_entries: list[dict]) -> list[dict]:
    """Strips each KB entry down to just {source, statement} before it goes
    into the prompt -- the model is never shown the internal "id" field
    (e.g. "residue_som_01"), so it physically cannot echo one into
    farmer-facing text."""
    return [{"source": e["source"], "statement": e["statement"]} for e in kb_entries]


# facts["data_sources"] uses stable snake_case ids (matched elsewhere, e.g.
# app.advisor.verify's SOURCE_CITATION_PATTERNS, and the report PDF) -- but
# those same raw ids ("nasa_power") were showing up verbatim in
# farmer-facing text because the model was shown them directly in facts_json.
# This is a presentation-only mapping applied just before the prompt is
# built; it never touches the `facts` object used for verification.
DATA_SOURCE_DISPLAY_NAMES = {
    "nasa_power": "NASA POWER",
    "isric_soilgrids": "ISRIC SoilGrids",
    "sky_to_soil_rotation_optimizer": "Sky-to-Soil's rotation optimizer",
    "ornl_modis_mod13q1": "MODIS satellite vegetation data",
    "usda_fao_texture_class_typical_values": "FAO soil-type reference values",
}


def _facts_for_prompt(facts: dict) -> dict:
    data_sources = facts.get("data_sources")
    if not data_sources:
        return facts
    return {
        **facts,
        "data_sources": [
            {**d, "source": DATA_SOURCE_DISPLAY_NAMES.get(d["source"], d["source"])} for d in data_sources
        ],
    }


def build_explain_messages(facts: dict, kb_entries: list[dict], current_crops: list[str], language: str) -> list[dict]:
    language_name = LANGUAGE_NAMES.get(language, LANGUAGE_NAMES["en"])
    system = SYSTEM_RULES.format(extension_line=EXTENSION_OFFICER_LINE.get(language, EXTENSION_OFFICER_LINE["en"]))
    user = EXPLAIN_TASK_TEMPLATE.format(
        facts_json=_dump(_facts_for_prompt(facts)),
        kb_json=_dump(_kb_for_prompt(kb_entries)),
        current_crops=", ".join(current_crops) or "no current crops given",
        language_name=language_name,
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_explain_rewrite_messages(
    facts: dict, kb_entries: list[dict], current_crops: list[str], language: str, issues: list[str]
) -> list[dict]:
    language_name = LANGUAGE_NAMES.get(language, LANGUAGE_NAMES["en"])
    system = SYSTEM_RULES.format(extension_line=EXTENSION_OFFICER_LINE.get(language, EXTENSION_OFFICER_LINE["en"]))
    user = REWRITE_TASK_TEMPLATE.format(
        issues_json=_dump(issues),
        facts_json=_dump(_facts_for_prompt(facts)),
        kb_json=_dump(_kb_for_prompt(kb_entries)),
        current_crops=", ".join(current_crops) or "no current crops given",
        language_name=language_name,
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_chat_messages(facts: dict, kb_entries: list[dict], current_crops: list[str], language: str, question: str) -> list[dict]:
    language_name = LANGUAGE_NAMES.get(language, LANGUAGE_NAMES["en"])
    system = SYSTEM_RULES.format(extension_line=EXTENSION_OFFICER_LINE.get(language, EXTENSION_OFFICER_LINE["en"]))
    user = CHAT_TASK_TEMPLATE.format(
        facts_json=_dump(_facts_for_prompt(facts)),
        kb_json=_dump(_kb_for_prompt(kb_entries)),
        current_crops=", ".join(current_crops) or "no current crops given",
        question=question,
        language_name=language_name,
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_chat_rewrite_messages(
    facts: dict, kb_entries: list[dict], current_crops: list[str], language: str, question: str, issues: list[str]
) -> list[dict]:
    language_name = LANGUAGE_NAMES.get(language, LANGUAGE_NAMES["en"])
    system = SYSTEM_RULES.format(extension_line=EXTENSION_OFFICER_LINE.get(language, EXTENSION_OFFICER_LINE["en"]))
    user = CHAT_REWRITE_TASK_TEMPLATE.format(
        issues_json=_dump(issues),
        facts_json=_dump(_facts_for_prompt(facts)),
        kb_json=_dump(_kb_for_prompt(kb_entries)),
        current_crops=", ".join(current_crops) or "no current crops given",
        question=question,
        language_name=language_name,
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]
