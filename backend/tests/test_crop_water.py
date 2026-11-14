from app.science.crop_water import (
    crop_seasonal_water_need,
    effective_rainfall,
    kc_daily_schedule,
)

WHEAT_KC = [
    {"stage": "initial", "length_days": 15, "kc": 0.4},
    {"stage": "development", "length_days": 25, "kc": 0.7},
    {"stage": "mid", "length_days": 50, "kc": 1.15},
    {"stage": "late", "length_days": 30, "kc": 0.4},
]


def test_kc_daily_schedule_length_matches_total_duration():
    schedule = kc_daily_schedule(WHEAT_KC)
    assert len(schedule) == 15 + 25 + 50 + 30


def test_kc_daily_schedule_starts_at_initial_and_ends_near_late_kc():
    schedule = kc_daily_schedule(WHEAT_KC)
    assert schedule[0] == 0.4
    assert schedule[-1] == 0.4  # last day of late-stage interpolation reaches Kc_end


def test_kc_daily_schedule_is_monotonic_increasing_through_development():
    schedule = kc_daily_schedule(WHEAT_KC)
    dev_start, dev_end = 15, 15 + 25
    dev_segment = schedule[dev_start:dev_end]
    assert all(dev_segment[i] <= dev_segment[i + 1] for i in range(len(dev_segment) - 1))


def test_effective_rainfall_below_250mm_threshold():
    # USDA SCS formula: Peff = P * (125 - 0.2P) / 125
    p = 100
    expected = p * (125 - 0.2 * p) / 125
    assert effective_rainfall(p) == round(expected, 2)


def test_effective_rainfall_above_250mm_threshold():
    p = 300
    expected = 125 + 0.1 * p
    assert effective_rainfall(p) == round(expected, 2)


def test_effective_rainfall_never_negative():
    assert effective_rainfall(0) == 0.0
    assert effective_rainfall(-10) == 0.0


def test_crop_seasonal_water_need_computes_deficit():
    duration = sum(s["length_days"] for s in WHEAT_KC)
    et0_daily = [5.0] * duration  # flat 5 mm/day ET0
    precip_daily = [0.0] * duration  # bone dry season -> full deficit expected

    result = crop_seasonal_water_need(WHEAT_KC, et0_daily, precip_daily)

    assert result["days_covered"] == duration
    assert result["total_rainfall_mm"] == 0.0
    assert result["effective_rainfall_mm"] == 0.0
    assert result["etc_total_mm"] > 0
    # No rainfall at all -> deficit equals total crop water need.
    assert result["water_deficit_mm"] == result["etc_total_mm"]


def test_crop_seasonal_water_need_with_rainfall_reduces_deficit():
    duration = sum(s["length_days"] for s in WHEAT_KC)
    et0_daily = [5.0] * duration
    dry = crop_seasonal_water_need(WHEAT_KC, et0_daily, [0.0] * duration)
    wet = crop_seasonal_water_need(WHEAT_KC, et0_daily, [3.0] * duration)
    assert wet["water_deficit_mm"] < dry["water_deficit_mm"]
