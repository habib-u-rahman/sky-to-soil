"""2-year / 4-season rotation generator and scorer.

Generates every agronomically valid 2-year rotation (Y1_kharif, Y1_rabi,
Y2_kharif, Y2_rabi; at most one slot may be left fallow), scores each on
five 0-100 sub-scores (water_fit, heat_risk, soil_health, soil_suitability,
land_use), combines them with farmer priority weights, and returns the top
N plus the Pareto-optimal set.

Scoring uses a day-of-year CLIMATOLOGY (typical year), not one specific
historical year -- see app/science/climatology.py.
"""

from __future__ import annotations

from itertools import product

from app.data.crop_repo import INCOME_PROXY, SOWING_START, crops_by_id, crops_for_season
from app.science.climatology import apply_stress_scenario, extract_window
from app.science.crop_water import crop_seasonal_water_need
from app.science.et0 import et0_hargreaves
from app.science.heat_stress import count_heat_stress_days
from app.science.soil_suitability import crop_soil_suitability

SLOTS = ["Y1_kharif", "Y1_rabi", "Y2_kharif", "Y2_rabi"]
SLOT_SEASON = {"Y1_kharif": "kharif", "Y1_rabi": "rabi", "Y2_kharif": "kharif", "Y2_rabi": "rabi"}

# Pareto front is computed over at most this many top-base-score candidates,
# to keep O(n^2) dominance comparisons fast even with thousands of candidates.
PARETO_CANDIDATE_CAP = 300

RESIDUE_SCORE = {"low": 33.0, "medium": 66.0, "high": 100.0}

# A rotation with no cropped slots at all (should be impossible once the
# <=1-fallow cap below is applied, but kept as a defensive fallback for
# slot_avg if it's ever called with zero filled slots).
NEUTRAL_EMPTY_SLOT = 50.0

# A 2-year/4-season rotation may leave at most this many seasons fallow.
# Cover/fodder crops (berseem etc.) are real crop ids, not None, so they
# count as cropped and are unaffected by this cap.
MAX_FALLOW_SLOTS = 1

# Fixed weight given to the land-use/income sub-score in every
# priority-weighted score, on top of whatever the farmer's own priority
# sliders contribute -- this is what keeps a fallow-heavy rotation from
# winning purely by minimizing water/heat exposure: idle land always costs
# something, regardless of what the farmer says they care about.
LAND_USE_BASELINE_WEIGHT = 0.2


def _crop_water_and_heat(crop: dict, climatology: dict[int, dict] | None, lat: float) -> dict:
    """Per-crop water_fit and heat_risk sub-scores (0-100), independent of
    soil and of the specific rotation it appears in."""
    if climatology is None:
        return {"water_fit": 50.0, "heat_risk": 50.0, "neutral_defaults": True}

    start_month, start_day = SOWING_START[crop["id"]]
    window = extract_window(climatology, start_month, start_day, crop["duration_days"])

    tmax = window["tmax"]
    tmin = window["tmin"]
    tmean = window["tmean"]
    precip = [p if p is not None else 0.0 for p in window["precip"]]
    start_doy = window["start_doy"]

    et0_daily = []
    for i in range(len(tmax)):
        if tmax[i] is None or tmin[i] is None or tmean[i] is None:
            et0_daily.append(0.0)
            continue
        doy = ((start_doy - 1 + i) % 365) + 1
        et0_daily.append(et0_hargreaves(tmax[i], tmin[i], tmean[i], doy, lat))

    water = crop_seasonal_water_need(crop["kc_stages"], et0_daily, precip)
    etc_total = water["etc_total_mm"]
    deficit = max(water["water_deficit_mm"], 0.0)
    water_fit = 100.0 if etc_total <= 0 else max(0.0, 100.0 * (1 - min(deficit / etc_total, 1.0)))

    tmax_for_heat = [t if t is not None else 0.0 for t in tmax]
    heat = count_heat_stress_days(tmax_for_heat, crop["kc_stages"], crop["heat_sensitive_stage"], crop["critical_temp_c"])
    pct_hot = heat["pct_window_days_hot"] or 0.0
    heat_risk = max(0.0, 100.0 - 2.5 * pct_hot)

    return {
        "water_fit": round(water_fit, 1),
        "heat_risk": round(heat_risk, 1),
        "water_detail": water,
        "heat_detail": heat,
        "neutral_defaults": False,
    }


def _build_crop_metric_cache(climatology: dict[int, dict] | None, soil_layers: list[dict] | None, lat: float) -> dict:
    cache = {}
    for crop in crops_by_id().values():
        wh = _crop_water_and_heat(crop, climatology, lat)
        suitability = crop_soil_suitability(crop, soil_layers)
        cache[crop["id"]] = {
            "water_fit": wh["water_fit"],
            "heat_risk": wh["heat_risk"],
            "neutral_defaults": wh["neutral_defaults"],
            "suitability": suitability["score"],
            "suitability_used_defaults": suitability["used_defaults"],
            "family": crop["family"],
            "n_fixing": crop["n_fixing"],
            "residue_contribution": crop["residue_contribution"],
            "rooting_depth_m": crop["rooting_depth_m"],
            "name": crop["name"],
        }
    return cache


def _generate_candidate_slot_assignments() -> list[dict]:
    """Every valid combination of crop-ids (or None for fallow) across the 4
    slots. Sugarcane (duration ~1 year) is treated as occupying exactly 2
    consecutive slots as one block; it is excluded from single-slot
    assignment to avoid agronomically meaningless half-placements."""
    kharif_ids = [c["id"] for c in crops_for_season("kharif") if c["id"] != "sugarcane"]
    rabi_ids = [c["id"] for c in crops_for_season("rabi") if c["id"] != "sugarcane"]
    kharif_opts = kharif_ids + [None]
    rabi_opts = rabi_ids + [None]

    candidates = []
    for yk1, yr1, yk2, yr2 in product(kharif_opts, rabi_opts, kharif_opts, rabi_opts):
        candidates.append({"Y1_kharif": yk1, "Y1_rabi": yr1, "Y2_kharif": yk2, "Y2_rabi": yr2})

    # Sugarcane blocks: occupies 2 consecutive slots together.
    slot_pairs = [("Y1_kharif", "Y1_rabi"), ("Y1_rabi", "Y2_kharif"), ("Y2_kharif", "Y2_rabi")]
    for pair in slot_pairs:
        remaining = [s for s in SLOTS if s not in pair]
        # remaining[0] season options, remaining[1] season options (sugarcane excluded again)
        opts0 = (kharif_ids if SLOT_SEASON[remaining[0]] == "kharif" else rabi_ids) + [None]
        opts1 = (kharif_ids if SLOT_SEASON[remaining[1]] == "kharif" else rabi_ids) + [None]
        for v0, v1 in product(opts0, opts1):
            cand = {pair[0]: "sugarcane", pair[1]: "sugarcane", remaining[0]: v0, remaining[1]: v1}
            candidates.append(cand)

    # At most MAX_FALLOW_SLOTS season may be left fallow. A real Punjab
    # farmer rotation leaves little land idle across 2 years; without this
    # cap, a mostly-fallow candidate can out-score every real cropping
    # choice simply by having less exposure to water/heat risk to average
    # over. This also drops the fully-fallow ("abandon the field") case.
    candidates = [c for c in candidates if sum(1 for v in c.values() if v is None) <= MAX_FALLOW_SLOTS]

    return candidates


def _closeness_score(slots: dict, current_crops: list[str]) -> float:
    filled = [c for c in slots.values() if c]
    if not filled or not current_crops:
        return 0.0
    matches = sum(1 for c in filled if c in current_crops)
    return round(100.0 * matches / len(filled), 1)


def _land_use_score(slots: dict) -> float:
    """Average per-slot income proxy (0-100) over all 4 slots, with a
    fallow slot contributing exactly 0 -- an explicit land-use/income
    penalty for leaving land idle, independent of water/heat/soil fit."""
    values = [INCOME_PROXY.get(c, 0) if c else 0.0 for c in slots.values()]
    return round(sum(values) / len(SLOTS), 1)


def _soil_health_score(slots: dict, cache: dict) -> dict:
    filled = [(slot, crop_id) for slot, crop_id in slots.items() if crop_id]
    if not filled:
        return {"score": 50.0, "legumes": [], "families": set(), "residue_score": 50.0, "root_range": 0.0}

    metas = [cache[crop_id] for _, crop_id in filled]
    n = len(metas)

    legumes = [m["name"] for m in metas if m["n_fixing"]]
    legume_score = min(100.0, 100.0 * (len(legumes) / 2.0))

    families = {m["family"] for m in metas}
    # Denominator is the full 4-slot rotation, not just filled slots -- a
    # rotation that only crops 1 of 4 seasons shouldn't score as "perfectly
    # diverse" just because its one crop trivially has no repeats.
    diversity_score = 100.0 * len(families) / len(SLOTS)

    ordered_crops = [slots[s] for s in SLOTS]
    pairs = [(ordered_crops[i], ordered_crops[i + 1]) for i in range(3)]
    valid_pairs = [(a, b) for a, b in pairs if a and b]
    if valid_pairs:
        broken = sum(1 for a, b in valid_pairs if cache[a]["family"] != cache[b]["family"])
        family_break_score = 100.0 * broken / len(valid_pairs)
    else:
        family_break_score = 100.0

    # Same reasoning: residue build-up over the full 2-year window is what
    # matters, so unplanted seasons (contributing zero residue) count in the
    # denominator rather than being skipped.
    residue_score = sum(RESIDUE_SCORE[m["residue_contribution"]] for m in metas) / len(SLOTS)

    depths = [m["rooting_depth_m"] for m in metas]
    root_range = max(depths) - min(depths) if len(depths) > 1 else 0.0
    root_variety_score = min(100.0, 100.0 * root_range / 1.5)

    score = round((legume_score + diversity_score + family_break_score + residue_score + root_variety_score) / 5, 1)
    return {
        "score": score,
        "legumes": legumes,
        "families": families,
        "residue_score": round(residue_score, 1),
        "root_range": round(root_range, 2),
        "family_break_score": round(family_break_score, 1),
    }


def _build_reasons_and_warnings(slots: dict, cache: dict, sub_scores: dict, soil_health_detail: dict) -> tuple[list[str], list[str]]:
    reasons, warnings = [], []
    filled = [(slot, crop_id) for slot, crop_id in slots.items() if crop_id]

    if soil_health_detail["legumes"]:
        reasons.append(
            f"Includes {', '.join(soil_health_detail['legumes'])} (nitrogen-fixing), building soil nitrogen for the crops that follow."
        )
    if len(soil_health_detail["families"]) == len(filled) and len(filled) > 1:
        reasons.append("Every crop in this rotation is from a different plant family, which breaks pest and disease cycles.")
    if soil_health_detail.get("family_break_score", 100) < 100:
        warnings.append("Two consecutive seasons share the same plant family, raising pest/disease carryover risk.")
    if soil_health_detail["root_range"] >= 0.8:
        reasons.append("Rooting depths vary widely across the rotation, which helps build soil structure at multiple depths.")
    if soil_health_detail["residue_score"] >= 80:
        reasons.append("High-residue crops in this rotation should meaningfully build soil organic matter over time.")

    if sub_scores["water_fit"] >= 80:
        reasons.append("Seasonal crop water demand is well matched to expected rainfall, with low irrigation risk.")
    elif sub_scores["water_fit"] < 50:
        warnings.append("This rotation likely needs significant supplemental irrigation to meet crop water demand.")

    if sub_scores["heat_risk"] >= 80:
        reasons.append("Heat-sensitive growth stages mostly avoid the hottest days of the year.")
    elif sub_scores["heat_risk"] < 40:
        warnings.append("At least one crop faces serious heat-stress risk during its sensitive growth stage under current climate.")

    if sub_scores["soil_suitability"] < 50:
        warnings.append("At least one crop is a weak match for local soil pH/texture; consider amendments or a substitute crop.")

    if any(c is None for c in slots.values()):
        warnings.append("Includes a fallow season with no crop income.")

    if any(cache[c]["neutral_defaults"] for _, c in filled):
        warnings.append("Water and heat scores used neutral defaults because climate data was unavailable.")
    if any(cache[c]["suitability_used_defaults"] for _, c in filled):
        warnings.append("Soil suitability used default assumptions because local soil data was unavailable.")

    if not reasons:
        reasons.append("A workable rotation for this season sequence; no standout strengths or risks identified.")

    return reasons, warnings


def _score_candidate(slots: dict, cache: dict, priorities: dict, current_crops: list[str]) -> dict:
    filled = [c for c in slots.values() if c]

    # water_fit/heat_risk/soil_suitability are judged PER CROPPED SEASON --
    # averaged only over the slots that actually have a crop in them, each
    # relative to what that specific crop needs. A fallow slot contributes
    # nothing here (neither a bonus nor a penalty): its cost is accounted
    # for separately and explicitly by land_use below, not by diluting
    # these climate/soil-fit averages with a stand-in value that could
    # accidentally pull a water-stressed rotation's average UP.
    def slot_avg(field: str) -> float:
        values = [cache[c][field] for c in slots.values() if c]
        if not values:
            return NEUTRAL_EMPTY_SLOT
        return round(sum(values) / len(values), 1)

    water_fit = slot_avg("water_fit")
    heat_risk = slot_avg("heat_risk")
    soil_suitability = slot_avg("suitability")
    soil_health_detail = _soil_health_score(slots, cache)
    soil_health = soil_health_detail["score"]
    land_use = _land_use_score(slots)

    sub_scores = {
        "water_fit": water_fit,
        "heat_risk": heat_risk,
        "soil_health": soil_health,
        "soil_suitability": soil_suitability,
        "land_use": land_use,
    }
    base_score = round(sum(sub_scores.values()) / len(sub_scores), 1)

    closeness = _closeness_score(slots, current_crops)

    weight_terms = [
        (priorities.get("save_water", 0), water_fit),
        (priorities.get("build_soil", 0), soil_health),
        (priorities.get("lower_climate_risk", 0), heat_risk),
        (priorities.get("stay_close_to_current", 0), closeness),
        (LAND_USE_BASELINE_WEIGHT, land_use),
    ]
    if priorities.get("income_proxy") is not None:
        weight_terms.append((priorities["income_proxy"], land_use))

    total_weight = sum(w for w, _ in weight_terms)
    priority_weighted = (
        round(sum(w * s for w, s in weight_terms) / total_weight, 1) if total_weight > 0 else base_score
    )

    reasons, warnings = _build_reasons_and_warnings(slots, cache, sub_scores, soil_health_detail)

    return {
        "rotation": dict(slots),
        "sub_scores": sub_scores,
        "base_score_0_100": base_score,
        "priority_weighted_score_0_100": priority_weighted,
        "reasons": reasons,
        "warnings": warnings,
    }


def _is_dominated(a: dict, b: dict) -> bool:
    """True if candidate b dominates candidate a (b >= a on all 5 sub-scores,
    strictly greater on at least one)."""
    keys = ["water_fit", "heat_risk", "soil_health", "soil_suitability", "land_use"]
    all_ge = all(b["sub_scores"][k] >= a["sub_scores"][k] for k in keys)
    any_gt = any(b["sub_scores"][k] > a["sub_scores"][k] for k in keys)
    return all_ge and any_gt


def pareto_optimal_set(scored: list[dict]) -> list[dict]:
    pool = sorted(scored, key=lambda r: r["base_score_0_100"], reverse=True)[:PARETO_CANDIDATE_CAP]
    front = []
    for candidate in pool:
        if not any(_is_dominated(candidate, other) for other in pool if other is not candidate):
            front.append(candidate)
    return front


def score_all_rotations(
    climatology: dict[int, dict] | None,
    soil_layers: list[dict] | None,
    priorities: dict,
    current_crops: list[str],
    lat: float,
    top_n: int = 10,
) -> dict:
    cache = _build_crop_metric_cache(climatology, soil_layers, lat)
    candidates = _generate_candidate_slot_assignments()

    scored = [_score_candidate(slots, cache, priorities, current_crops) for slots in candidates]
    scored.sort(key=lambda r: r["priority_weighted_score_0_100"], reverse=True)

    top = scored[:top_n]
    pareto = pareto_optimal_set(scored)

    return {
        "candidates_evaluated": len(candidates),
        "top": top,
        "pareto_optimal": pareto,
    }


def stress_test_rotations(
    climatology: dict[int, dict] | None,
    soil_layers: list[dict] | None,
    priorities: dict,
    current_crops: list[str],
    lat: float,
    delta_temp_c: float,
    rainfall_change_pct: float,
    top_n: int = 10,
) -> dict:
    """Re-scores the farmer's current top-N rotations under a shifted
    climate (+delta_temp_c, rainfall scaled by rainfall_change_pct) and
    reports a resilience score: 100 = no degradation, 0 = total collapse."""
    baseline_cache = _build_crop_metric_cache(climatology, soil_layers, lat)
    candidates = _generate_candidate_slot_assignments()

    baseline_scored = [_score_candidate(slots, baseline_cache, priorities, current_crops) for slots in candidates]
    baseline_scored.sort(key=lambda r: r["priority_weighted_score_0_100"], reverse=True)
    top_candidates = baseline_scored[:top_n]

    stressed_climatology = (
        apply_stress_scenario(climatology, delta_temp_c, rainfall_change_pct) if climatology is not None else None
    )
    stressed_cache = _build_crop_metric_cache(stressed_climatology, soil_layers, lat)

    results = []
    for baseline in top_candidates:
        slots = baseline["rotation"]
        stressed = _score_candidate(slots, stressed_cache, priorities, current_crops)

        baseline_score = baseline["base_score_0_100"]
        stressed_score = stressed["base_score_0_100"]
        drop = round(baseline_score - stressed_score, 1)
        resilience = round(max(0.0, min(100.0, 100 - drop)), 1)

        results.append(
            {
                "rotation": slots,
                "baseline_score_0_100": baseline_score,
                "stressed_score_0_100": stressed_score,
                "score_drop": drop,
                "resilience_score_0_100": resilience,
                "reasons": stressed["reasons"][:3],
            }
        )

    results.sort(key=lambda r: r["resilience_score_0_100"], reverse=True)
    return {"results": results}
