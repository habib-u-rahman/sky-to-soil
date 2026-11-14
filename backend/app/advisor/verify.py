"""Rule-based verifier for AI Agronomist output. No LLM involved here --
every check is a plain Python/regex rule against the `facts` object that was
handed to the writer, so "verified" is a mechanical guarantee, not a
self-report from the model that produced the text.

Checks:
1. Every number mentioned in the text must match a numeric value actually
   present in `facts` (rounding-tolerant), except small structural integers
   (1-4: "2-year rotation", "Y1"/"Y2", "3 tips", list numbering).
2. Every crop named (English or Urdu) must be part of the rotation or the
   farmer's current crops.
3. Every data-source citation named must be one of the retrieved KB sources
   or the live data sources actually used.
4. No yield/profit guarantee language (English or Urdu).
5. Must include a line recommending confirmation with a local extension
   officer.
"""

from __future__ import annotations

import re

from app.data.crop_repo import crops_by_id

# Urdu display names for the 14 crops in crops.json, used so Urdu-language
# text can be checked against the same allow-list as English text.
CROP_NAME_UR = {
    "wheat": "گندم",
    "rice": "چاول",
    "maize": "مکئی",
    "cotton": "کپاس",
    "sugarcane": "گنا",
    "chickpea": "چنا",
    "lentil": "مسور",
    "mungbean": "مونگ",
    "sorghum": "جوار",
    "pearl_millet": "باجرا",
    "mustard": "سرسوں",
    "potato": "آلو",
    "berseem_clover": "برسیم",
    "soybean": "سویابین",
}

# Arabic-Indic (U+0660-0669) and Extended Arabic-Indic / Urdu (U+06F0-06F9)
# digits -> ASCII, so number-checking works on Urdu-script text.
_DIGIT_MAP = {}
for _i in range(10):
    _DIGIT_MAP[chr(0x0660 + _i)] = str(_i)
    _DIGIT_MAP[chr(0x06F0 + _i)] = str(_i)

_NUMBER_RE = re.compile(r"(?<![A-Za-z0-9_])[-+]?\d+(?:\.\d+)?")
_LIST_MARKER_RE = re.compile(r"(?m)^\s*\d+[.)]\s+")
_SLOT_LABEL_RE = re.compile(r"(?i)\bY\d\b")
# "FAO-56" is a fixed source label, not a number claim -- without this, the
# hyphen (not itself a letter/digit) would let the number regex's lookbehind
# treat the "56" as a bare standalone number.
_FAO56_LABEL_RE = re.compile(r"(?i)\bFAO-?56\b")

# 1-4: "2-year rotation", "Y1"/"Y2" (stripped separately), "3 tips", list
# numbering. 100: every sub-score/base-score in this app is explicitly on a
# 0-100 scale, so "X/100" or "out of 100" is a scale label, not a new claim.
STRUCTURAL_NUMBERS = {1.0, 2.0, 3.0, 4.0, 100.0}

GUARANTEE_PATTERNS = [
    r"guarantee", r"guaranteed", r"promise[sd]?", r"\bwill definitely\b",
    r"certainly increase", r"assured profit", r"100% yield", r"risk[- ]free",
    r"ضمانت", r"یقینی\s*منافع", r"یقینی\s*طور\s*پر\s*(زیادہ|منافع)", r"ضرور\s*منافع",
]

# Negation markers checked in a window around a guarantee-word match --
# English typically negates before the word ("not a guarantee"), Urdu
# typically negates after it ("ضمانت نہیں", literally "guarantee not") --
# so a guarantee word is only flagged if NEITHER direction shows a negation
# nearby. This lets the required "not a guarantee of yield/income"
# disclaimer through without weakening the check against actual promises.
_NEGATION_RE = re.compile(r"(?i)\b(not|no|isn't|aren't|cannot|can't|won't|without)\b|نہیں|نہ")
_GUARANTEE_CONTEXT_WINDOW = 40

EXTENSION_OFFICER_PATTERNS = [
    r"extension officer",
    r"توسیعی\s*اہلکار",
    r"زرعی\s*ماہر",
]

# source label -> regex patterns that would appear in generated text if the
# model cites that source.
SOURCE_CITATION_PATTERNS = {
    "nasa_power": [r"nasa power", r"\bpower\b"],
    "isric_soilgrids": [r"isric", r"soilgrids"],
    "sky_to_soil_rotation_optimizer": [r"sky-to-soil", r"rotation optimizer"],
    "FAO-56": [r"fao-?56"],
    "FAO conservation agriculture": [r"fao conservation agriculture", r"conservation agriculture"],
    "legume nitrogen fixation": [r"nitrogen fixation", r"rhizobia"],
    "crop residue and soil organic matter": [r"soil organic matter", r"\bsom\b"],
    "crop diversity and pest breaks": [r"pest break", r"disease carryover"],
    "heat stress at flowering": [r"heat stress at flowering"],
    "water-saving practices": [r"water-saving"],
}


def _normalize_digits(text: str) -> str:
    return "".join(_DIGIT_MAP.get(ch, ch) for ch in text)


def _extract_numbers(text: str) -> list[float]:
    text = _normalize_digits(text)
    text = _LIST_MARKER_RE.sub("", text)
    text = _SLOT_LABEL_RE.sub("", text)
    text = _FAO56_LABEL_RE.sub("", text)
    return [float(m) for m in _NUMBER_RE.findall(text)]


def _flatten_facts_numbers(obj) -> set[float]:
    numbers: set[float] = set()
    if isinstance(obj, bool):
        return numbers
    if isinstance(obj, (int, float)):
        numbers.add(round(float(obj), 2))
        numbers.add(round(float(obj)))
    elif isinstance(obj, dict):
        for v in obj.values():
            numbers |= _flatten_facts_numbers(v)
    elif isinstance(obj, list):
        for v in obj:
            numbers |= _flatten_facts_numbers(v)
    return numbers


def _number_matches(n: float, allowed: set[float], tolerance_abs: float = 0.6, tolerance_rel: float = 0.02) -> bool:
    if n in STRUCTURAL_NUMBERS:
        return True
    for a in allowed:
        tol = max(tolerance_abs, abs(a) * tolerance_rel)
        if abs(n - a) <= tol:
            return True
    return False


def _check_numbers(text: str, facts: dict) -> list[str]:
    allowed = _flatten_facts_numbers(facts)
    issues = []
    seen_bad = set()
    for n in _extract_numbers(text):
        if n in seen_bad:
            continue
        if not _number_matches(n, allowed):
            seen_bad.add(n)
            issues.append(f"number '{n:g}' in text does not match any value in facts")
    return issues


def _allowed_crop_ids(facts: dict) -> set[str]:
    rotation_crop_ids = set(facts.get("per_crop", {}).keys())
    current = {c for c in facts.get("current_crops", [])}
    return rotation_crop_ids | current


def _check_crop_names(text: str, facts: dict) -> list[str]:
    allowed_ids = _allowed_crop_ids(facts)
    all_crops = crops_by_id()
    lowered = text.lower()
    issues = []
    for cid, crop in all_crops.items():
        mentioned = crop["name"].lower() in lowered or CROP_NAME_UR.get(cid, " ") in text
        if mentioned and cid not in allowed_ids:
            issues.append(f"mentions crop '{crop['name']}' which is not in this rotation or the farmer's current crops")
    return issues


def _check_sources(text: str, kb_sources: set[str], data_sources: set[str]) -> list[str]:
    allowed = kb_sources | data_sources
    lowered = text.lower()
    issues = []
    for source, patterns in SOURCE_CITATION_PATTERNS.items():
        if source in allowed:
            continue
        for pat in patterns:
            if re.search(pat, lowered):
                issues.append(f"cites source '{source}' which was not among the retrieved/used sources")
                break
    return issues


def _check_guarantee_language(text: str) -> list[str]:
    for pat in GUARANTEE_PATTERNS:
        for m in re.finditer(pat, text, re.IGNORECASE):
            window = text[max(0, m.start() - _GUARANTEE_CONTEXT_WINDOW) : m.end() + _GUARANTEE_CONTEXT_WINDOW]
            if _NEGATION_RE.search(window):
                continue
            return [f"contains yield/profit guarantee language matching /{pat}/"]
    return []


def _check_extension_officer_mention(full_text: str) -> list[str]:
    for pat in EXTENSION_OFFICER_PATTERNS:
        if re.search(pat, full_text, re.IGNORECASE):
            return []
    return ["missing a recommendation to confirm with a local extension officer"]


def verify_output(
    farmer_text: str,
    technical_note: str,
    facts: dict,
    kb_entries: list[dict],
    require_extension_officer: bool = True,
) -> dict:
    kb_sources = {e["source"] for e in kb_entries}
    data_sources = {d["source"] for d in facts.get("data_sources", []) if d.get("status") == "ok"}
    # sky_to_soil_rotation_optimizer is always "used" (it produced the rotation itself).
    data_sources.add("sky_to_soil_rotation_optimizer")

    combined_text = f"{farmer_text}\n{technical_note}"

    issues: list[str] = []
    issues += _check_numbers(combined_text, facts)
    issues += _check_crop_names(combined_text, facts)
    issues += _check_sources(combined_text, kb_sources, data_sources)
    issues += _check_guarantee_language(combined_text)
    if require_extension_officer:
        issues += _check_extension_officer_mention(combined_text)

    return {"verified": len(issues) == 0, "issues": issues}
