"""Heat stress: count days above a crop's critical temperature that fall
within its heat-sensitive growth stage window."""

from __future__ import annotations


def stage_day_ranges(kc_stages: list[dict]) -> dict[str, tuple[int, int]]:
    """Map each FAO-56 stage name to its (start_day, end_day) offsets from
    sowing, 0-indexed, inclusive start / exclusive end."""
    ranges = {}
    cursor = 0
    for stage in kc_stages:
        start = cursor
        end = cursor + stage["length_days"]
        ranges[stage["stage"]] = (start, end)
        cursor = end
    return ranges


# Stage names in crops.json use botanical terms (e.g. "anthesis/grain-filling")
# rather than the generic FAO-56 stage names (initial/development/mid/late).
# Map each crop's heat-sensitive stage to the FAO-56 stage it falls within.
HEAT_STAGE_TO_FAO56_STAGE = {
    "anthesis/grain-filling": "mid",
    "flowering/anthesis": "mid",
    "silking/pollination": "mid",
    "flowering/boll set": "mid",
    "grand growth/tillering": "development",
    "flowering/pod set": "mid",
    "flowering/panicle exsertion": "mid",
    "tuber initiation/bulking": "development",
    "vegetative regrowth after cutting": "mid",
}


def heat_sensitive_window(kc_stages: list[dict], heat_sensitive_stage: str) -> tuple[int, int]:
    """Resolve a crop's named heat-sensitive stage to a (start_day, end_day)
    offset window from sowing. Falls back to the 'mid' FAO-56 stage (where
    flowering/reproductive development typically occurs) if the stage name
    isn't recognised."""
    fao56_stage = HEAT_STAGE_TO_FAO56_STAGE.get(heat_sensitive_stage, "mid")
    ranges = stage_day_ranges(kc_stages)
    return ranges.get(fao56_stage, ranges.get("mid", (0, 0)))


def count_heat_stress_days(
    tmax_daily: list[float], kc_stages: list[dict], heat_sensitive_stage: str, critical_temp_c: float
) -> dict:
    """Count how many days within the crop's heat-sensitive stage window
    (relative to sowing day 0) have Tmax > critical_temp_c."""
    start, end = heat_sensitive_window(kc_stages, heat_sensitive_stage)
    window = tmax_daily[start:end]
    hot_days = sum(1 for t in window if t is not None and t > critical_temp_c)
    return {
        "window_start_day": start,
        "window_end_day": end,
        "window_length_days": end - start,
        "days_tmax_gt_critical": hot_days,
        "pct_window_days_hot": round(100 * hot_days / (end - start), 1) if end > start else None,
    }
