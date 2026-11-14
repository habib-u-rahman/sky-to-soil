"""ISRIC SoilGrids REST client.

Verified against the live API on 2026-11-14:
  GET https://rest.isric.org/soilgrids/v2.0/properties/query
      ?lon=73.08&lat=31.42&property=phh2o&property=clay&property=sand
      &property=silt&property=soc&property=nitrogen&property=cec
      &depth=0-5cm&depth=5-15cm&depth=15-30cm&value=mean
  -> HTTP 200, correct JSON schema, BUT every single property/depth value
     was `null` for this point. Re-tested with a different nearby point
     (31.40, 73.10), with a totally different reference point
     (-72.0, 43.0 -- that call also failed, this time with a timeout), and
     with no `value` filter (to see raw Q0.05/Q0.5/Q0.95/mean/uncertainty)
     -- still all null. This points to a live ISRIC backend data outage
     rather than a malformed request. We handle this by detecting an
     all-null response and surfacing status="manual_input_needed" per the
     spec, instead of silently returning nulls as if they were real zeros.
"""

from __future__ import annotations

from app.core.cache import cache_get, cache_key, cache_set
from app.core.http import UpstreamError, get_json

SOILGRIDS_BASE_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"

PROPERTIES = ["phh2o", "clay", "sand", "silt", "soc", "nitrogen", "cec"]
DEPTHS = ["0-5cm", "5-15cm", "15-30cm"]

# SoilGrids "d_factor" conversions to human units (mapped_units -> target_units),
# confirmed from the live response's "unit_measure" block for each property.
D_FACTORS = {
    "phh2o": 10,       # pH*10 -> pH
    "clay": 10,        # g/kg -> %
    "sand": 10,        # g/kg -> %
    "silt": 10,        # g/kg -> %
    "soc": 10,         # dg/kg -> g/kg
    "nitrogen": 100,   # cg/kg -> g/kg
    "cec": 10,         # mmol(c)/kg -> cmol(c)/kg
}

FIELD_NAME = {
    "phh2o": "phh2o",
    "clay": "clay_pct",
    "sand": "sand_pct",
    "silt": "silt_pct",
    "soc": "soc_g_kg",
    "nitrogen": "nitrogen_g_kg",
    "cec": "cec_cmol_kg",
}


async def fetch_soil_profile(lat: float, lon: float) -> dict:
    """Returns:
        {"ok": True, "all_null": bool, "layers": [{"depth", "phh2o", "clay_pct", ...}, ...], "cache_hit": False}
      or {"ok": False, "error": "..."}
    """
    key = cache_key("soilgrids", round(lat, 4), round(lon, 4))
    cached = cache_get(key)
    if cached is not None:
        cached["cache_hit"] = True
        return cached

    params = [("lon", lon), ("lat", lat)] + [("property", p) for p in PROPERTIES] + [
        ("depth", d) for d in DEPTHS
    ] + [("value", "mean")]

    try:
        # ISRIC's public API has been observed to be slow/flaky (see module
        # docstring) -- use a tighter timeout and fewer retries than the
        # default so a degraded upstream can't stall a request for minutes.
        raw = await get_json(SOILGRIDS_BASE_URL, params=params, timeout_seconds=15.0, max_retries=2)
    except UpstreamError as exc:
        return {"ok": False, "error": str(exc), "cache_hit": False}

    try:
        layers_raw = raw["properties"]["layers"]
    except (KeyError, TypeError):
        return {"ok": False, "error": "unexpected SoilGrids response shape", "cache_hit": False}

    # layer name -> depth label -> raw mean
    by_property: dict[str, dict[str, float | None]] = {}
    for layer in layers_raw:
        name = layer["name"]
        by_property[name] = {}
        for depth_block in layer["depths"]:
            label = depth_block["label"]
            mean = depth_block["values"].get("mean")
            if mean is not None:
                mean = mean / D_FACTORS[name]
            by_property[name][label] = mean

    layers_out = []
    any_value = False
    any_null = False
    for depth in DEPTHS:
        row = {"depth": depth}
        for prop in PROPERTIES:
            val = by_property.get(prop, {}).get(depth)
            if val is not None:
                any_value = True
            else:
                any_null = True
            row[FIELD_NAME[prop]] = val
        layers_out.append(row)

    result = {
        "ok": True,
        "all_null": not any_value,
        "any_null": any_null,
        "layers": layers_out,
        "cache_hit": False,
    }
    cache_set(key, result)
    return result
