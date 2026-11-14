"""Crop x soil suitability: pH range match + texture class match.

A simplified (not full USDA texture triangle) texture classifier is used --
good enough to steer rotation choices in a decision-support tool, not a
substitute for a proper soil texture lab test.
"""

from __future__ import annotations

DEFAULT_SUITABILITY_SCORE = 70.0  # used when soil data is unavailable


def classify_texture(clay_pct: float | None, sand_pct: float | None, silt_pct: float | None) -> str | None:
    if clay_pct is None:
        return None
    if clay_pct >= 35:
        return "clay"
    if clay_pct >= 20:
        return "clay_loam"
    if sand_pct is not None and sand_pct >= 50:
        return "sandy_loam"
    if silt_pct is not None and silt_pct >= 50:
        return "silt_loam"
    return "loam"


def weighted_profile_mean(layers: list[dict], field: str) -> float | None:
    """Depth-weighted mean of a soil property across 0-5/5-15/15-30 cm
    layers (weights proportional to layer thickness: 5, 10, 15 cm)."""
    weights = {"0-5cm": 5, "5-15cm": 10, "15-30cm": 15}
    total_w, total_v = 0.0, 0.0
    for layer in layers:
        v = layer.get(field)
        w = weights.get(layer.get("depth"), 0)
        if v is not None:
            total_w += w
            total_v += w * v
    if total_w == 0:
        return None
    return round(total_v / total_w, 2)


def score_ph(ph: float | None, ph_min: float, ph_max: float) -> float:
    if ph is None:
        return DEFAULT_SUITABILITY_SCORE
    if ph_min <= ph <= ph_max:
        return 100.0
    distance = min(abs(ph - ph_min), abs(ph - ph_max))
    return max(0.0, 100.0 - distance * 40.0)


def score_texture(texture_class: str | None, texture_preference: list[str]) -> float:
    if texture_class is None:
        return DEFAULT_SUITABILITY_SCORE
    return 100.0 if texture_class in texture_preference else 40.0


def crop_soil_suitability(crop: dict, layers: list[dict] | None) -> dict:
    """Returns {"score": 0-100, "ph": float|None, "texture_class": str|None,
    "used_defaults": bool}."""
    if not layers:
        return {"score": DEFAULT_SUITABILITY_SCORE, "ph": None, "texture_class": None, "used_defaults": True}

    ph = weighted_profile_mean(layers, "phh2o")
    clay = weighted_profile_mean(layers, "clay_pct")
    sand = weighted_profile_mean(layers, "sand_pct")
    silt = weighted_profile_mean(layers, "silt_pct")
    texture_class = classify_texture(clay, sand, silt)

    ph_score = score_ph(ph, crop["ph_min"], crop["ph_max"])
    texture_score = score_texture(texture_class, crop["texture_preference"])
    used_defaults = ph is None and texture_class is None

    return {
        "score": round((ph_score + texture_score) / 2, 1),
        "ph": ph,
        "texture_class": texture_class,
        "used_defaults": used_defaults,
    }
