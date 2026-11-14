"""Climate shift analysis: baseline (2001-2012) vs recent (2013-latest)
comparison of temperature, seasonal rainfall, root-zone wetness, plus
Mann-Kendall trend + Sen's slope on annual series.

Seasons are configurable (default: kharif = May-Oct, rabi = Nov-Apr, which
wraps the calendar year boundary) so this module works outside South Asia
too -- pass a different SeasonConfig-shaped dict for other regions.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict

from app.science.trend_stats import mann_kendall_test, sens_slope

DEFAULT_SEASONS = {
    "kharif": {"start_month": 5, "end_month": 10},
    "rabi": {"start_month": 11, "end_month": 4},
}


def _parse_power_date(date_str: str) -> dt.date:
    return dt.date(int(date_str[0:4]), int(date_str[4:6]), int(date_str[6:8]))


def _season_year(date: dt.date, start_month: int, end_month: int) -> int:
    """Group a date into the 'season-year' it belongs to. For a season that
    does not wrap the year (start_month <= end_month), season_year = date.year
    if the month is within range, else it does not belong to this season.
    For a wrapping season (e.g. Nov-Apr), Nov/Dec belong to season_year =
    date.year; Jan-Apr belong to season_year = date.year - 1 (continuing the
    season that started the previous November)."""
    wraps = start_month > end_month
    if not wraps:
        return date.year
    if date.month >= start_month:
        return date.year
    return date.year - 1


def _in_season(date: dt.date, start_month: int, end_month: int) -> bool:
    wraps = start_month > end_month
    if not wraps:
        return start_month <= date.month <= end_month
    return date.month >= start_month or date.month <= end_month


def _mean(values: list[float]) -> float | None:
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return round(sum(clean) / len(clean), 3)


def _period_stats(
    series: dict[str, dict[str, float | None]],
    start_year: int,
    end_year: int,
    seasons: dict,
) -> dict:
    """Compute mean Tmax/Tmin, per-season hot day counts, per-season
    rainfall, and mean root-zone wetness for one period [start_year, end_year]."""

    tmax_series = series["T2M_MAX"]
    tmin_series = series["T2M_MIN"]
    precip_series = series["PRECTOTCORR"]
    gwetroot_series = series["GWETROOT"]

    all_tmax, all_tmin, all_gwetroot = [], [], []
    hot35_by_season_year: dict[str, dict[int, int]] = {s: defaultdict(int) for s in seasons}
    hot40_by_season_year: dict[str, dict[int, int]] = {s: defaultdict(int) for s in seasons}
    rain_by_season_year: dict[str, dict[int, float]] = {s: defaultdict(float) for s in seasons}
    season_days_seen: dict[str, set] = {s: set() for s in seasons}

    for date_str, tmax in tmax_series.items():
        date = _parse_power_date(date_str)
        if not (start_year <= date.year <= end_year):
            continue

        tmin = tmin_series.get(date_str)
        precip = precip_series.get(date_str)
        gwetroot = gwetroot_series.get(date_str)

        if tmax is not None:
            all_tmax.append(tmax)
        if tmin is not None:
            all_tmin.append(tmin)
        if gwetroot is not None:
            all_gwetroot.append(gwetroot)

        for season_name, cfg in seasons.items():
            sm, em = cfg["start_month"], cfg["end_month"]
            if not _in_season(date, sm, em):
                continue
            sy = _season_year(date, sm, em)
            season_days_seen[season_name].add(sy)
            if tmax is not None and tmax > 35:
                hot35_by_season_year[season_name][sy] += 1
            if tmax is not None and tmax > 40:
                hot40_by_season_year[season_name][sy] += 1
            if precip is not None:
                rain_by_season_year[season_name][sy] += precip

    def avg_over_years(by_year: dict[int, float], years_seen: set) -> float | None:
        if not years_seen:
            return None
        total = sum(by_year.get(y, 0) for y in years_seen)
        return round(total / len(years_seen), 2)

    hot35 = {s: avg_over_years(hot35_by_season_year[s], season_days_seen[s]) for s in seasons}
    hot40 = {s: avg_over_years(hot40_by_season_year[s], season_days_seen[s]) for s in seasons}
    # Keyed "{season}_mm" to match the SeasonalRainfall schema (kharif_mm/rabi_mm),
    # unlike hot35/hot40 which match SeasonalHotDays' plain kharif/rabi fields.
    rain = {f"{s}_mm": avg_over_years(rain_by_season_year[s], season_days_seen[s]) for s in seasons}

    return {
        "mean_tmax_c": _mean(all_tmax),
        "mean_tmin_c": _mean(all_tmin),
        "hot_days_gt35_by_season": hot35,
        "hot_days_gt40_by_season": hot40,
        "seasonal_rainfall_mm": rain,
        "mean_root_zone_wetness": _mean(all_gwetroot),
    }


def _annual_series(series: dict[str, float | None], agg: str, start_year: int, end_year: int) -> list[tuple[int, float]]:
    """agg='mean' or 'sum'. Returns sorted [(year, value), ...] skipping years
    with no data."""
    by_year: dict[int, list[float]] = defaultdict(list)
    for date_str, value in series.items():
        if value is None:
            continue
        date = _parse_power_date(date_str)
        if start_year <= date.year <= end_year:
            by_year[date.year].append(value)

    out = []
    for year in sorted(by_year):
        vals = by_year[year]
        out.append((year, sum(vals) if agg == "sum" else sum(vals) / len(vals)))
    return out


def _seasonal_annual_series(
    series: dict[str, float | None], start_month: int, end_month: int, start_year: int, end_year: int
) -> list[tuple[int, float]]:
    by_season_year: dict[int, float] = defaultdict(float)
    seen: set = set()
    for date_str, value in series.items():
        date = _parse_power_date(date_str)
        if not (start_year - 1 <= date.year <= end_year + 1):
            continue
        if not _in_season(date, start_month, end_month):
            continue
        sy = _season_year(date, start_month, end_month)
        if sy < start_year or sy > end_year:
            continue
        seen.add(sy)
        if value is not None:
            by_season_year[sy] += value
    return [(y, by_season_year.get(y, 0.0)) for y in sorted(seen)]


def analyze_climate_shift(
    power_series: dict[str, dict[str, float | None]],
    start_year: int,
    end_year: int,
    seasons: dict | None = None,
    split_year: int = 2013,
) -> dict:
    """Full climate shift analysis given raw POWER series
    (series["T2M_MAX"]["20010101"] = 12.3, etc.)."""

    seasons = seasons or DEFAULT_SEASONS

    baseline_end = split_year - 1
    baseline = _period_stats(power_series, start_year, baseline_end, seasons)
    recent = _period_stats(power_series, split_year, end_year, seasons)

    baseline_out = {
        "period_label": f"{start_year}-{baseline_end}",
        "start_year": start_year,
        "end_year": baseline_end,
        "n_years": baseline_end - start_year + 1,
        **baseline,
    }
    recent_out = {
        "period_label": f"{split_year}-{end_year}",
        "start_year": split_year,
        "end_year": end_year,
        "n_years": end_year - split_year + 1,
        **recent,
    }

    def delta(a, b):
        if a is None or b is None:
            return None
        return round(b - a, 3)

    deltas = {
        "mean_tmax_c": delta(baseline["mean_tmax_c"], recent["mean_tmax_c"]),
        "mean_tmin_c": delta(baseline["mean_tmin_c"], recent["mean_tmin_c"]),
        "mean_root_zone_wetness": delta(baseline["mean_root_zone_wetness"], recent["mean_root_zone_wetness"]),
    }
    for season_name in seasons:
        deltas[f"{season_name}_rainfall_mm"] = delta(
            baseline["seasonal_rainfall_mm"].get(f"{season_name}_mm"),
            recent["seasonal_rainfall_mm"].get(f"{season_name}_mm"),
        )

    # Trends over the FULL period.
    trends = []

    annual_tmax = _annual_series(power_series["T2M_MAX"], "mean", start_year, end_year)
    annual_tmin = _annual_series(power_series["T2M_MIN"], "mean", start_year, end_year)
    annual_gwetroot = _annual_series(power_series["GWETROOT"], "mean", start_year, end_year)

    def trend_entry(name: str, series_pairs: list[tuple[int, float]]) -> dict:
        if len(series_pairs) < 4:
            return {
                "variable": name,
                "mk_trend": "no trend",
                "mk_p_value": None,
                "sen_slope_per_year": None,
                "significant_at_0_10": False,
            }
        years = [y for y, _ in series_pairs]
        values = [v for _, v in series_pairs]
        mk = mann_kendall_test(values)
        slope = sens_slope(values, years)
        return {
            "variable": name,
            "mk_trend": mk["trend"],
            "mk_p_value": mk["p_value"],
            "sen_slope_per_year": slope,
            "significant_at_0_10": bool(mk["p_value"] is not None and mk["p_value"] < 0.10),
        }

    trends.append(trend_entry("annual_mean_tmax_c", annual_tmax))
    trends.append(trend_entry("annual_mean_tmin_c", annual_tmin))
    trends.append(trend_entry("root_zone_wetness", annual_gwetroot))

    for season_name, cfg in seasons.items():
        rain_pairs = _seasonal_annual_series(
            power_series["PRECTOTCORR"], cfg["start_month"], cfg["end_month"], start_year, end_year
        )
        trends.append(trend_entry(f"{season_name}_rainfall_mm", rain_pairs))

    return {
        "baseline": baseline_out,
        "recent": recent_out,
        "deltas": deltas,
        "trends": trends,
    }
