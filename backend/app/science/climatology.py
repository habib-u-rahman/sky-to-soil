"""Day-of-year climatology built from NASA POWER daily series.

The rotation optimizer scores crops against a *typical* year (the mean of
each calendar day-of-year across the recent period), not one specific
historical year -- that's the right basis for a forward-looking "what
rotation should I plant next" recommendation, as opposed to the backward-
looking climate shift report in app/science/climate.py.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict

DOY_VARS = ["T2M_MAX", "T2M_MIN", "T2M", "PRECTOTCORR", "GWETROOT", "ALLSKY_SFC_SW_DWN", "RH2M", "WS2M"]

VAR_TO_FIELD = {
    "T2M_MAX": "tmax",
    "T2M_MIN": "tmin",
    "T2M": "tmean",
    "PRECTOTCORR": "precip",
    "GWETROOT": "gwetroot",
    "ALLSKY_SFC_SW_DWN": "swdwn",
    "RH2M": "rh",
    "WS2M": "ws",
}


def build_doy_climatology(power_series: dict, recent_start_year: int | None = None) -> dict[int, dict]:
    """Returns {doy (1-365): {"tmax": .., "tmin": .., "tmean": .., "precip": ..,
    "gwetroot": .., "swdwn": .., "rh": .., "ws": ..}}, averaged across all
    available years (or years >= recent_start_year if given). Day 366 (leap
    day) values are folded into day 365 so every year lines up on a 365-day
    cycle.
    """
    sums: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    counts: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for power_var, field in VAR_TO_FIELD.items():
        series = power_series.get(power_var, {})
        for date_str, value in series.items():
            if value is None:
                continue
            date = dt.date(int(date_str[0:4]), int(date_str[4:6]), int(date_str[6:8]))
            if recent_start_year is not None and date.year < recent_start_year:
                continue
            doy = min(date.timetuple().tm_yday, 365)
            sums[doy][field] += value
            counts[doy][field] += 1

    climatology = {}
    for doy in range(1, 366):
        day_vals = {}
        for field in VAR_TO_FIELD.values():
            c = counts[doy][field]
            day_vals[field] = round(sums[doy][field] / c, 3) if c > 0 else None
        climatology[doy] = day_vals

    return climatology


def extract_window(climatology: dict[int, dict], start_month: int, start_day: int, length_days: int) -> dict[str, list]:
    """Extract `length_days` consecutive days of climatology starting at
    (start_month, start_day), wrapping cyclically past day 365 if the window
    crosses the year boundary (e.g. a rabi crop sown in November running
    into the next calendar year)."""
    start_doy = dt.date(2001, start_month, start_day).timetuple().tm_yday  # 2001: non-leap reference year

    tmax, tmin, tmean, precip, gwetroot, swdwn, rh, ws = [], [], [], [], [], [], [], []
    for offset in range(length_days):
        doy = ((start_doy - 1 + offset) % 365) + 1
        day = climatology.get(doy, {})
        tmax.append(day.get("tmax"))
        tmin.append(day.get("tmin"))
        tmean.append(day.get("tmean"))
        precip.append(day.get("precip"))
        gwetroot.append(day.get("gwetroot"))
        swdwn.append(day.get("swdwn"))
        rh.append(day.get("rh"))
        ws.append(day.get("ws"))

    return {
        "tmax": tmax,
        "tmin": tmin,
        "tmean": tmean,
        "precip": precip,
        "gwetroot": gwetroot,
        "swdwn": swdwn,
        "rh": rh,
        "ws": ws,
        "start_doy": start_doy,
    }


def apply_stress_scenario(climatology: dict[int, dict], delta_temp_c: float, rainfall_change_pct: float) -> dict[int, dict]:
    """Return a shifted copy of the climatology: +delta_temp_c to all
    temperature fields, and rainfall scaled by (1 + rainfall_change_pct/100)."""
    shifted = {}
    rain_factor = 1 + (rainfall_change_pct / 100.0)
    for doy, day in climatology.items():
        new_day = dict(day)
        for field in ("tmax", "tmin", "tmean"):
            if new_day.get(field) is not None:
                new_day[field] = round(new_day[field] + delta_temp_c, 3)
        if new_day.get("precip") is not None:
            new_day["precip"] = round(max(new_day["precip"] * rain_factor, 0.0), 3)
        shifted[doy] = new_day
    return shifted
