"""Crop water need: ETc = Kc x ET0 (FAO-56 dual/single crop coefficient
approach, single Kc here), effective rainfall (USDA Soil Conservation
Service formula), and seasonal water deficit.

Reference: FAO-56 (Allen et al. 1998), chapters 6 (ETc) and Annex on
effective rainfall; USDA SCS formula as reproduced in FAO Irrigation Water
Management Training Manual No. 3 (Brouwer & Heibloem, 1986).
"""

from __future__ import annotations


def kc_daily_schedule(kc_stages: list[dict]) -> list[float]:
    """Build a day-by-day Kc curve from the 4 FAO-56 stages
    [initial, development, mid, late], linearly interpolating Kc during the
    development stage (initial->mid) and late stage (mid->end), per FAO-56
    chapter 6."""
    by_stage = {s["stage"]: s for s in kc_stages}
    initial, development, mid, late = (
        by_stage["initial"],
        by_stage["development"],
        by_stage["mid"],
        by_stage["late"],
    )

    daily: list[float] = [initial["kc"]] * initial["length_days"]

    dev_len = development["length_days"]
    for d in range(dev_len):
        frac = (d + 1) / dev_len
        daily.append(initial["kc"] + frac * (mid["kc"] - initial["kc"]))

    daily += [mid["kc"]] * mid["length_days"]

    late_len = late["length_days"]
    for d in range(late_len):
        frac = (d + 1) / late_len
        daily.append(mid["kc"] + frac * (late["kc"] - mid["kc"]))

    return daily


def effective_rainfall(total_rainfall_mm: float) -> float:
    """USDA SCS formula for effective rainfall from total rainfall over a
    period. Note: the SCS formula is defined per-month; applying it to a
    multi-month seasonal total (as we do here) is a simplification suitable
    for a comparative decision-support tool, not a precise irrigation
    schedule."""
    p = max(total_rainfall_mm, 0.0)
    if p <= 250:
        return round(p * (125 - 0.2 * p) / 125, 2)
    return round(125 + 0.1 * p, 2)


def crop_seasonal_water_need(kc_stages: list[dict], et0_daily: list[float], precip_daily: list[float]) -> dict:
    """Given a crop's Kc stages and daily ET0/precipitation series starting
    at sowing date, return total crop water need, rainfall, effective
    rainfall, and water deficit for the season."""
    kc_daily = kc_daily_schedule(kc_stages)
    n = min(len(kc_daily), len(et0_daily))

    etc_values = [kc_daily[i] * et0_daily[i] for i in range(n)]
    etc_total = sum(etc_values)

    rain_n = min(n, len(precip_daily))
    total_rainfall = sum(precip_daily[:rain_n])
    peff = effective_rainfall(total_rainfall)
    deficit = etc_total - peff

    return {
        "days_covered": n,
        "etc_total_mm": round(etc_total, 1),
        "total_rainfall_mm": round(total_rainfall, 1),
        "effective_rainfall_mm": peff,
        "water_deficit_mm": round(deficit, 1),
    }
