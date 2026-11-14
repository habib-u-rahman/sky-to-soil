"""Reference evapotranspiration (ET0), FAO-56 methods.

- Hargreaves (FAO-56 Eq. 52): needs only Tmax, Tmin, Tmean and extraterrestrial
  radiation Ra (computed from latitude + day-of-year) -- works with NASA
  POWER's T2M_MAX/T2M_MIN/T2M alone.
- Penman-Monteith (FAO-56 Eq. 6): the FAO reference-standard method; used
  automatically when all required inputs are available (Tmax, Tmin, RH2M,
  WS2M, ALLSKY_SFC_SW_DWN, elevation).

Reference: Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998). FAO
Irrigation and Drainage Paper 56.
"""

from __future__ import annotations

import math

SOLAR_CONSTANT = 0.0820  # MJ m^-2 min^-1


def _day_of_year_solar_params(day_of_year: int, lat_deg: float) -> tuple[float, float]:
    """Returns (dr, Ra) where dr = inverse relative distance Earth-Sun,
    Ra = extraterrestrial radiation (MJ m^-2 day^-1)."""
    lat_rad = math.radians(lat_deg)
    dr = 1 + 0.033 * math.cos(2 * math.pi / 365 * day_of_year)
    delta = 0.409 * math.sin(2 * math.pi / 365 * day_of_year - 1.39)  # solar declination

    x = -math.tan(lat_rad) * math.tan(delta)
    x = max(-1.0, min(1.0, x))
    ws = math.acos(x)  # sunset hour angle

    ra = (
        (24 * 60 / math.pi)
        * SOLAR_CONSTANT
        * dr
        * (ws * math.sin(lat_rad) * math.sin(delta) + math.cos(lat_rad) * math.cos(delta) * math.sin(ws))
    )
    return dr, ra


def et0_hargreaves(tmax_c: float, tmin_c: float, tmean_c: float, day_of_year: int, lat_deg: float) -> float:
    """FAO-56 Hargreaves equation (Eq. 52): ET0 = 0.0023 * (Tmean + 17.8) *
    (Tmax - Tmin)^0.5 * Ra, with Ra in mm/day equivalent (Ra_MJ * 0.408)."""
    _, ra_mj = _day_of_year_solar_params(day_of_year, lat_deg)
    ra_mm = 0.408 * ra_mj
    tdiff = max(tmax_c - tmin_c, 0.0)
    et0 = 0.0023 * (tmean_c + 17.8) * math.sqrt(tdiff) * ra_mm
    return round(max(et0, 0.0), 3)


def et0_penman_monteith(
    tmax_c: float,
    tmin_c: float,
    rh_mean_pct: float,
    wind_2m_ms: float,
    solar_rad_mj_m2_day: float,
    day_of_year: int,
    lat_deg: float,
    elevation_m: float = 200.0,
) -> float:
    """FAO-56 Penman-Monteith (Eq. 6) for a daily time step, grass reference
    crop (albedo 0.23, hc=0.12m)."""
    tmean = (tmax_c + tmin_c) / 2.0

    # Atmospheric pressure (Eq. 7)
    p = 101.3 * ((293 - 0.0065 * elevation_m) / 293) ** 5.26
    gamma = 0.000665 * p  # psychrometric constant (Eq. 8)

    def sat_vap_pressure(t):
        return 0.6108 * math.exp((17.27 * t) / (t + 237.3))

    es_tmax = sat_vap_pressure(tmax_c)
    es_tmin = sat_vap_pressure(tmin_c)
    es = (es_tmax + es_tmin) / 2.0

    # Slope of saturation vapour pressure curve at Tmean (Eq. 13)
    delta = (4098 * sat_vap_pressure(tmean)) / (tmean + 237.3) ** 2

    ea = es * (rh_mean_pct / 100.0)  # Eq. 19 (mean RH approximation)

    _, ra = _day_of_year_solar_params(day_of_year, lat_deg)
    rs = solar_rad_mj_m2_day
    rs_max = 0.75 * ra  # clear-sky approx (simplified, no elevation term beyond Ra)
    rs = min(rs, rs_max) if rs_max > 0 else rs

    rso = (0.75 + 2e-5 * elevation_m) * ra  # Eq. 37, clear-sky solar radiation
    rs_rso = min(rs / rso, 1.0) if rso > 0 else 0.0

    rns = (1 - 0.23) * rs  # net shortwave radiation (Eq. 38)

    sigma = 4.903e-9  # Stefan-Boltzmann, MJ K^-4 m^-2 day^-1
    tmax_k = tmax_c + 273.16
    tmin_k = tmin_c + 273.16
    rnl = (
        sigma
        * ((tmax_k**4 + tmin_k**4) / 2.0)
        * (0.34 - 0.14 * math.sqrt(max(ea, 0.0)))
        * (1.35 * rs_rso - 0.35)
    )  # Eq. 39, net longwave radiation
    rn = rns - rnl  # net radiation (Eq. 40)

    g = 0.0  # soil heat flux, assumed ~0 for daily step (FAO-56 simplification)

    numerator = 0.408 * delta * (rn - g) + gamma * (900 / (tmean + 273)) * wind_2m_ms * (es - ea)
    denominator = delta + gamma * (1 + 0.34 * wind_2m_ms)
    et0 = numerator / denominator
    return round(max(et0, 0.0), 3)
