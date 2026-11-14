from app.science.heat_stress import (
    count_heat_stress_days,
    heat_sensitive_window,
    stage_day_ranges,
)

WHEAT_KC = [
    {"stage": "initial", "length_days": 15, "kc": 0.4},
    {"stage": "development", "length_days": 25, "kc": 0.7},
    {"stage": "mid", "length_days": 50, "kc": 1.15},
    {"stage": "late", "length_days": 30, "kc": 0.4},
]


def test_stage_day_ranges_are_contiguous_and_non_overlapping():
    ranges = stage_day_ranges(WHEAT_KC)
    assert ranges["initial"] == (0, 15)
    assert ranges["development"] == (15, 40)
    assert ranges["mid"] == (40, 90)
    assert ranges["late"] == (90, 120)


def test_heat_sensitive_window_resolves_known_stage_name():
    window = heat_sensitive_window(WHEAT_KC, "anthesis/grain-filling")
    assert window == (40, 90)  # wheat's heat-sensitive stage maps to FAO-56 'mid'


def test_heat_sensitive_window_falls_back_to_mid_for_unknown_stage_name():
    window = heat_sensitive_window(WHEAT_KC, "some stage not in the lookup table")
    assert window == (40, 90)


def test_count_heat_stress_days_counts_only_within_window():
    duration = sum(s["length_days"] for s in WHEAT_KC)
    tmax_daily = [20.0] * duration
    # Inject hot days: 5 inside the mid (heat-sensitive) window, 5 outside it.
    for day in [45, 50, 55, 60, 65]:
        tmax_daily[day] = 40.0
    for day in [0, 5, 100, 110, 115]:
        tmax_daily[day] = 40.0

    result = count_heat_stress_days(tmax_daily, WHEAT_KC, "anthesis/grain-filling", critical_temp_c=32)

    assert result["window_start_day"] == 40
    assert result["window_end_day"] == 90
    assert result["days_tmax_gt_critical"] == 5


def test_count_heat_stress_days_zero_when_no_hot_days():
    duration = sum(s["length_days"] for s in WHEAT_KC)
    tmax_daily = [20.0] * duration
    result = count_heat_stress_days(tmax_daily, WHEAT_KC, "anthesis/grain-filling", critical_temp_c=32)
    assert result["days_tmax_gt_critical"] == 0
    assert result["pct_window_days_hot"] == 0.0
