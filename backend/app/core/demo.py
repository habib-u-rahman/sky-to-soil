"""Demo mode: serves a frozen, pre-fetched analysis for a farm near
Faisalabad, Pakistan (31.3053 N, 73.2144 E) so the app works with zero
network access. Activated on any endpoint via `?demo=true`.

This point was chosen (2026-11) over the original 31.42/73.08 (Faisalabad
CITY center, MODIS NDVI ~0.12 -- built-up land, not cropland) by testing a
handful of candidate points within 30km and checking each one's real MODIS
NDVI time series for a clear double-cropping signal. 31.3053/73.2144 (~18km
SE of the city, rural) shows a clean two-peaks-per-year pattern: a rabi
peak ~0.58-0.61 (Feb-Mar, wheat), a trough ~0.3-0.4 (Apr-May transition),
and a kharif peak ~0.70-0.77 (Jul-Aug), repeating across both 2022 and
2023 -- both peaks comfortably above 0.5.

Regenerate the frozen file with: python -m app.scripts.build_demo
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DEMO_FILE = Path(__file__).resolve().parent.parent / "data" / "demo_analysis.json"

DEMO_LOCATION = {"lat": 31.3053, "lon": 73.2144}


@lru_cache
def load_demo_analysis() -> dict | None:
    if not DEMO_FILE.exists():
        return None
    with open(DEMO_FILE, encoding="utf-8") as f:
        return json.load(f)
