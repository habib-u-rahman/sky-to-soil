import datetime as dt

from app.science.climate import analyze_climate_shift, _season_year, _in_season


def _build_power_series(start_year: int, end_year: int, warming_c: float = 0.0) -> dict:
    """Build a synthetic daily POWER series across start_year..end_year.
    `warming_c` is added to Tmax/Tmin for years >= 2013 to create a detectable
    shift, mimicking a real climate-shift scenario."""
    params = ["T2M_MAX", "T2M_MIN", "T2M", "PRECTOTCORR", "GWETROOT", "ALLSKY_SFC_SW_DWN", "RH2M", "WS2M"]
    series = {p: {} for p in params}

    date = dt.date(start_year, 1, 1)
    end = dt.date(end_year, 12, 31)
    while date <= end:
        key = date.strftime("%Y%m%d")
        extra = warming_c if date.year >= 2013 else 0.0
        # Seasonal-ish temperature wave so hot days appear in kharif (May-Oct)
        seasonal = 10 * (1 if 5 <= date.month <= 10 else -1)
        series["T2M_MAX"][key] = 28 + seasonal + extra
        series["T2M_MIN"][key] = 15 + seasonal * 0.5 + extra
        series["T2M"][key] = 22 + seasonal * 0.7 + extra
        series["PRECTOTCORR"][key] = 5.0 if 5 <= date.month <= 10 else 1.0
        series["GWETROOT"][key] = 0.4
        series["ALLSKY_SFC_SW_DWN"][key] = 20.0
        series["RH2M"][key] = 50.0
        series["WS2M"][key] = 2.0
        date += dt.timedelta(days=1)
    return series


def test_season_year_assignment_handles_wrap_around():
    # rabi = Nov-Apr: Nov/Dec belong to the year they occur in; Jan-Apr belong
    # to the PREVIOUS year's season.
    assert _season_year(dt.date(2020, 11, 15), 11, 4) == 2020
    assert _season_year(dt.date(2021, 2, 1), 11, 4) == 2020
    assert _season_year(dt.date(2021, 5, 1), 5, 10) == 2021


def test_in_season_wrap_around():
    assert _in_season(dt.date(2021, 12, 1), 11, 4) is True
    assert _in_season(dt.date(2021, 2, 1), 11, 4) is True
    assert _in_season(dt.date(2021, 7, 1), 11, 4) is False


def test_climate_shift_detects_warming_and_more_hot_days():
    series = _build_power_series(2005, 2020, warming_c=2.0)
    result = analyze_climate_shift(series, start_year=2005, end_year=2020)

    baseline = result["baseline"]
    recent = result["recent"]

    assert baseline["period_label"] == "2005-2012"
    assert recent["period_label"] == "2013-2020"

    # Recent period should be warmer given the synthetic +2C shift.
    assert recent["mean_tmax_c"] > baseline["mean_tmax_c"]
    assert result["deltas"]["mean_tmax_c"] > 0

    # More hot days (>35C) in kharif in the recent (warmer) period.
    assert recent["hot_days_gt35_by_season"]["kharif"] >= baseline["hot_days_gt35_by_season"]["kharif"]

    # Trend for annual mean Tmax should register as increasing given the
    # step-change warming embedded in the synthetic series.
    tmax_trend = next(t for t in result["trends"] if t["variable"] == "annual_mean_tmax_c")
    assert tmax_trend["mk_trend"] == "increasing"


def test_climate_shift_with_no_warming_shows_near_zero_delta():
    series = _build_power_series(2005, 2020, warming_c=0.0)
    result = analyze_climate_shift(series, start_year=2005, end_year=2020)
    assert abs(result["deltas"]["mean_tmax_c"]) < 0.5


def test_seasonal_rainfall_is_higher_in_kharif_than_rabi():
    series = _build_power_series(2005, 2015)
    result = analyze_climate_shift(series, start_year=2005, end_year=2015)
    kharif_rain = result["baseline"]["seasonal_rainfall_mm"]["kharif_mm"]
    rabi_rain = result["baseline"]["seasonal_rainfall_mm"]["rabi_mm"]
    assert kharif_rain > rabi_rain
