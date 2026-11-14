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
   are fine as plain structural language.
2. Only mention crop names that appear in FACTS (either in rotation_crops or current_crops). \
   Do not mention any other crop.
3. Only cite a data source or knowledge-base topic if it appears in KB or DATA_SOURCES below. \
   Do not invent sources.
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


def build_explain_messages(facts: dict, kb_entries: list[dict], current_crops: list[str], language: str) -> list[dict]:
    language_name = LANGUAGE_NAMES.get(language, LANGUAGE_NAMES["en"])
    system = SYSTEM_RULES.format(extension_line=EXTENSION_OFFICER_LINE.get(language, EXTENSION_OFFICER_LINE["en"]))
    user = EXPLAIN_TASK_TEMPLATE.format(
        facts_json=_dump(facts),
        kb_json=_dump(kb_entries),
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
        facts_json=_dump(facts),
        kb_json=_dump(kb_entries),
        current_crops=", ".join(current_crops) or "no current crops given",
        language_name=language_name,
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_chat_messages(facts: dict, kb_entries: list[dict], current_crops: list[str], language: str, question: str) -> list[dict]:
    language_name = LANGUAGE_NAMES.get(language, LANGUAGE_NAMES["en"])
    system = SYSTEM_RULES.format(extension_line=EXTENSION_OFFICER_LINE.get(language, EXTENSION_OFFICER_LINE["en"]))
    user = CHAT_TASK_TEMPLATE.format(
        facts_json=_dump(facts),
        kb_json=_dump(kb_entries),
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
        facts_json=_dump(facts),
        kb_json=_dump(kb_entries),
        current_crops=", ".join(current_crops) or "no current crops given",
        question=question,
        language_name=language_name,
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]
