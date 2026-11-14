"""Loads and indexes the crop knowledge base (app/data/crops.json)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

CROPS_JSON_PATH = Path(__file__).resolve().parent / "crops.json"

# Primary sowing start (month, day) used by the rotation engine to align a
# crop's day-of-year climatology window. Taken from each crop's
# `sowing_window` text in crops.json (first date mentioned there); crops with
# multiple sowing windows (e.g. mungbean spring-or-summer) use the window
# that matches their declared `season` so it lines up with the kharif/rabi
# slot it is scored into.
SOWING_START = {
    "wheat": (11, 1),
    "rice": (6, 1),
    "maize": (5, 15),
    "cotton": (4, 15),
    "sugarcane": (2, 1),
    "chickpea": (10, 15),
    "lentil": (10, 25),
    "mungbean": (7, 1),
    "sorghum": (6, 1),
    "pearl_millet": (6, 15),
    "mustard": (10, 1),
    "potato": (10, 15),
    "berseem_clover": (10, 15),
    "soybean": (6, 1),
}

# Rough relative income proxy (0-100), NOT real market price/yield data --
# used only to rank candidate rotations against each other when a farmer
# opts in to the optional income_proxy priority. High-value cash crops score
# higher; fallow scores 0 (no harvest).
INCOME_PROXY = {
    "wheat": 55,
    "rice": 70,
    "maize": 50,
    "cotton": 80,
    "sugarcane": 85,
    "chickpea": 60,
    "lentil": 55,
    "mungbean": 50,
    "sorghum": 40,
    "pearl_millet": 40,
    "mustard": 55,
    "potato": 75,
    "berseem_clover": 30,
    "soybean": 60,
}

TEXTURE_GROUPS = {
    "sand": ["sandy", "sandy_loam"],
    "loam": ["loam", "sandy_loam", "clay_loam", "silt_loam"],
    "clay": ["clay", "clay_loam"],
}


@lru_cache
def load_crops() -> list[dict]:
    with open(CROPS_JSON_PATH, encoding="utf-8") as f:
        return json.load(f)


@lru_cache
def crops_by_id() -> dict:
    return {c["id"]: c for c in load_crops()}


def crops_for_season(season: str) -> list[dict]:
    """season = 'kharif' or 'rabi'. Returns crops whose `season` field matches
    or is 'either'."""
    return [c for c in load_crops() if c["season"] == season or c["season"] == "either"]
