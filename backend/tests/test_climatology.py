import datetime as dt

from app.science.climatology import apply_stress_scenario, build_doy_climatology, extract_window


def _synthetic_power_series(years=range(2015, 2020)):
    params = ["T2M_MAX", "T2M_MIN", "T2M", "PRECTOTCORR", "GWETROOT", "ALLSKY_SFC_SW_DWN", "RH2M", "WS2M"]
    series = {p: {} for p in params}
    for year in years:
        date = dt.date(year, 1, 1)
        end = dt.date(year, 12, 31)
        while date <= end:
            key = date.strftime("%Y%m%d")
            series["T2M_MAX"][key] = 30.0
            series["T2M_MIN"][key] = 15.0
            series["T2M"][key] = 22.0
            series["PRECTOTCORR"][key] = 2.0
            series["GWETROOT"][key] = 0.35
            series["ALLSKY_SFC_SW_DWN"][key] = 18.0
            series["RH2M"][key] = 45.0
            series["WS2M"][key] = 2.0
            date += dt.timedelta(days=1)
    return series


def test_build_doy_climatology_averages_across_years():
    series = _synthetic_power_series()
    clim = build_doy_climatology(series)
    assert clim[1]["tmax"] == 30.0
    assert clim[1]["tmin"] == 15.0
    assert clim[200]["precip"] == 2.0
    assert len(clim) == 365


def test_build_doy_climatology_respects_recent_start_year_filter():
    series = _synthetic_power_series()
    # mutate 2019 to have a distinct value and check the filter picks it up
    series["T2M_MAX"]["20190101"] = 99.0
    clim_all = build_doy_climatology(series)
    clim_recent = build_doy_climatology(series, recent_start_year=2019)
    assert clim_all[1]["tmax"] < 99.0  # averaged with other years
    assert clim_recent[1]["tmax"] == 99.0  # only 2019 included


def test_extract_window_returns_requested_length():
    series = _synthetic_power_series()
    clim = build_doy_climatology(series)
    window = extract_window(clim, start_month=6, start_day=1, length_days=120)
    assert len(window["tmax"]) == 120
    assert all(v == 30.0 for v in window["tmax"])


def test_extract_window_wraps_past_year_end():
    series = _synthetic_power_series()
    clim = build_doy_climatology(series)
    # Nov 1 + 150 days wraps well past Dec 31into the next "calendar" cycle
    window = extract_window(clim, start_month=11, start_day=1, length_days=150)
    assert len(window["tmax"]) == 150
    assert all(v is not None for v in window["tmax"])


def test_apply_stress_scenario_shifts_temperature_and_rainfall():
    series = _synthetic_power_series()
    clim = build_doy_climatology(series)
    stressed = apply_stress_scenario(clim, delta_temp_c=1.5, rainfall_change_pct=-15)
    assert stressed[1]["tmax"] == 31.5
    assert stressed[1]["tmin"] == 16.5
    assert abs(stressed[1]["precip"] - 1.7) < 0.01  # 2.0 * 0.85


def test_apply_stress_scenario_rainfall_never_negative():
    series = _synthetic_power_series()
    clim = build_doy_climatology(series)
    stressed = apply_stress_scenario(clim, delta_temp_c=0, rainfall_change_pct=-500)
    assert stressed[1]["precip"] == 0.0
