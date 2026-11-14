"""Demo mode: serves a frozen, pre-fetched analysis for a farm near
Faisalabad, Pakistan (31.42 N, 73.08 E) so the app works with zero network
access. Activated on any endpoint via `?demo=true`.

Regenerate the frozen file with: python -m app.scripts.build_demo
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DEMO_FILE = Path(__file__).resolve().parent.parent / "data" / "demo_analysis.json"

DEMO_LOCATION = {"lat": 31.42, "lon": 73.08}


@lru_cache
def load_demo_analysis() -> dict | None:
    if not DEMO_FILE.exists():
        return None
    with open(DEMO_FILE, encoding="utf-8") as f:
        return json.load(f)
