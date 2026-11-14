from app.science.et0 import et0_hargreaves, et0_penman_monteith


def test_hargreaves_returns_positive_reasonable_value():
    # Faisalabad, Pakistan, a hot early-summer day.
    et0 = et0_hargreaves(tmax_c=38, tmin_c=22, tmean_c=30, day_of_year=150, lat_deg=31.42)
    assert 3.0 < et0 < 12.0


def test_hargreaves_increases_with_larger_diurnal_temperature_range():
    low_range = et0_hargreaves(tmax_c=30, tmin_c=25, tmean_c=27.5, day_of_year=150, lat_deg=31.42)
    high_range = et0_hargreaves(tmax_c=38, tmin_c=15, tmean_c=26.5, day_of_year=150, lat_deg=31.42)
    assert high_range > low_range


def test_hargreaves_never_negative_even_if_tmin_exceeds_tmax_input_error():
    et0 = et0_hargreaves(tmax_c=20, tmin_c=25, tmean_c=22, day_of_year=150, lat_deg=31.42)
    assert et0 >= 0.0


def test_penman_monteith_reasonable_range_for_hot_dry_day():
    # FAO-56 Example 18 style inputs (hot, moderately humid, windy day).
    et0 = et0_penman_monteith(
        tmax_c=34.8,
        tmin_c=25.6,
        rh_mean_pct=68,
        wind_2m_ms=2.078,
        solar_rad_mj_m2_day=22.07,
        day_of_year=269,
        lat_deg=-22.9,
        elevation_m=1100,
    )
    # FAO-56's own worked example for these inputs yields ET0 close to 5.7 mm/day;
    # we assert a tolerant range rather than the exact published figure.
    assert 4.5 < et0 < 7.0


def test_penman_monteith_increases_with_wind_speed():
    base = dict(
        tmax_c=32, tmin_c=20, rh_mean_pct=50, solar_rad_mj_m2_day=20, day_of_year=150, lat_deg=31.42
    )
    low_wind = et0_penman_monteith(wind_2m_ms=1.0, **base)
    high_wind = et0_penman_monteith(wind_2m_ms=5.0, **base)
    assert high_wind > low_wind


def test_penman_monteith_increases_with_solar_radiation():
    base = dict(tmax_c=32, tmin_c=20, rh_mean_pct=50, wind_2m_ms=2.0, day_of_year=150, lat_deg=31.42)
    low_rad = et0_penman_monteith(solar_rad_mj_m2_day=10, **base)
    high_rad = et0_penman_monteith(solar_rad_mj_m2_day=25, **base)
    assert high_rad > low_rad
