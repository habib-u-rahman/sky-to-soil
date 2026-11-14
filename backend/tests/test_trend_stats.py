from app.science.trend_stats import mann_kendall_test, sens_slope


def test_mann_kendall_detects_clear_increasing_trend():
    values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    result = mann_kendall_test(values)
    assert result["trend"] == "increasing"
    assert result["p_value"] < 0.10


def test_mann_kendall_detects_clear_decreasing_trend():
    values = [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
    result = mann_kendall_test(values)
    assert result["trend"] == "decreasing"
    assert result["p_value"] < 0.10


def test_mann_kendall_no_trend_for_noise_around_constant():
    # Alternating up/down -> net S close to 0 -> "no trend"
    values = [5, 6, 5, 6, 5, 6, 5, 6, 5, 6]
    result = mann_kendall_test(values)
    assert result["trend"] == "no trend"


def test_mann_kendall_short_series_returns_no_trend():
    result = mann_kendall_test([1, 2, 3])
    assert result["trend"] == "no trend"
    assert result["p_value"] is None


def test_sens_slope_perfect_linear_series():
    values = [10, 12, 14, 16, 18]  # slope = 2 per unit time
    slope = sens_slope(values)
    assert slope == 2.0


def test_sens_slope_with_custom_time_index():
    years = [2001, 2005, 2010]
    values = [10, 18, 28]  # not perfectly linear, median of pairwise slopes
    slope = sens_slope(values, years)
    assert slope is not None
    assert 1.5 < slope < 3.0


def test_sens_slope_single_value_returns_none():
    assert sens_slope([5]) is None
