"""Pre-fetches a full farm analysis for the demo farm near Faisalabad,
Pakistan (31.3053 N, 73.2144 E) and freezes it to app/data/demo_analysis.json
so `?demo=true` works with zero network access.

Run with:  python -m app.scripts.build_demo
"""

from __future__ import annotations

import asyncio
import json

from app import services
from app.advisor import facts as advisor_facts
from app.advisor.graph import run_chat, run_explain
from app.core.demo import DEMO_FILE, DEMO_LOCATION
from app.core.sources import now_iso, source_meta
from app.data.crop_repo import crops_by_id, load_crops
from app.routers.soil import SOIL_PRESETS
from app.science.climatology import build_doy_climatology
from app.science.rotation_engine import score_all_rotations, stress_test_rotations

DEMO_SOIL_FALLBACK_TEXTURE = "loam"
DEMO_SOIL_DEPTHS = ["0-5cm", "5-15cm", "15-30cm"]

DEMO_PRIORITIES = {
    "save_water": 0.3,
    "build_soil": 0.3,
    "lower_climate_risk": 0.2,
    "stay_close_to_current": 0.2,
    "income_proxy": None,
}
DEMO_CURRENT_CROPS = ["wheat", "cotton"]

# Fixed sample questions precomputed into the demo cache so POST
# /advisor/chat?demo=true never needs a live Groq call for these -- any
# other question in demo mode falls back to the deterministic template.
DEMO_CHAT_QUESTIONS = {
    "en": [
        "Why was this rotation recommended for my farm?",
        "How much extra irrigation will wheat need in this rotation?",
        "Will this rotation guarantee a good profit?",
        "What should I watch out for with this rotation?",
        "How is my local climate changing?",
    ],
    "ur": [
        "یہ فصل کی ترتیب میرے فارم کے لیے کیوں تجویز کی گئی؟",
        "اس ترتیب میں گندم کو کتنی اضافی آبپاشی کی ضرورت ہوگی؟",
        "کیا یہ ترتیب اچھے منافع کی ضمانت دیتی ہے؟",
        "اس ترتیب کے ساتھ مجھے کس بات کا خیال رکھنا چاہیے؟",
        "میرے علاقے کی آب و ہوا کیسے بدل رہی ہے؟",
    ],
}


def _explain_payload(result: dict, language: str) -> dict:
    return {
        "text": result.get("farmer_text", ""),
        "technical_note": result.get("technical_note", ""),
        "language": language,
        "verified": result.get("verified", False),
        "issues": result.get("issues", []),
        "rewrites_used": result.get("rewrites_used", 0),
        "facts_used": result["facts"],
        "kb_sources": sorted({e["source"] for e in result.get("kb", [])}),
        "model_used": result.get("model_used", "fallback_template"),
    }


def _chat_payload(result: dict, language: str) -> dict:
    return {
        "answer": result.get("answer", ""),
        "language": language,
        "verified": result.get("verified", False),
        "issues": result.get("issues", []),
        "answerable": result.get("answerable", False),
        "rewrites_used": result.get("rewrites_used", 0),
        "facts_used": result["facts"],
        "kb_sources": sorted({e["source"] for e in result.get("kb", [])}),
        "model_used": result.get("model_used", "fallback_template"),
    }


async def main():
    lat, lon = DEMO_LOCATION["lat"], DEMO_LOCATION["lon"]
    warnings = []

    print(f"Fetching climate for ({lat}, {lon}) from NASA POWER...")
    climate_raw = await services.get_climate_shift(lat, lon)

    climate = None
    climatology = None
    if climate_raw.get("error"):
        warnings.append(f"climate: NASA POWER unavailable ({climate_raw['source']['message']})")
        print("  POWER FAILED:", climate_raw["source"]["message"])
    else:
        climatology = build_doy_climatology(climate_raw["_power_series"], recent_start_year=2013)
        climate_raw.pop("_power_series", None)
        climate_raw.pop("error", None)
        climate_raw["location"] = {"lat": lat, "lon": lon}
        climate = climate_raw
        print("  OK")

    print("Fetching soil from ISRIC SoilGrids...")
    soil = await services.get_soil_profile(lat, lon)
    soil["location"] = {"lat": lat, "lon": lon}
    print(" ", soil["status"])
    if soil["status"] != "ok":
        # SoilGrids has no usable data at this point. Rather than leave the
        # demo dashboard with an empty soil table and a "Partial data"
        # warning, fill it from the "loam" soil-type preset -- the same
        # preset a real farmer would pick in the setup wizard's "Choose
        # your soil type" picker -- and label it clearly as estimated
        # rather than measured, instead of pretending it's satellite data.
        print(f"  (SoilGrids unavailable: {soil['message']!r} -- filling with the '{DEMO_SOIL_FALLBACK_TEXTURE}' preset)")
        preset = next(p for p in SOIL_PRESETS if p["texture"] == DEMO_SOIL_FALLBACK_TEXTURE)
        soil = {
            "location": {"lat": lat, "lon": lon},
            "layers": [
                {
                    "depth": depth,
                    "phh2o": preset["phh2o"],
                    "clay_pct": preset["clay_pct"],
                    "sand_pct": preset["sand_pct"],
                    "silt_pct": preset["silt_pct"],
                    "soc_g_kg": preset["soc_g_kg"],
                    "nitrogen_g_kg": preset["nitrogen_g_kg"],
                    "cec_cmol_kg": preset["cec_cmol_kg"],
                }
                for depth in DEMO_SOIL_DEPTHS
            ],
            "status": "ok",
            "message": f"Estimated from the '{DEMO_SOIL_FALLBACK_TEXTURE}' soil-type preset (ISRIC SoilGrids had no data at this exact point).",
            "source": source_meta("usda_fao_texture_class_typical_values", "ok", None, False),
        }

    print("Fetching NDVI from ORNL DAAC MODIS (2018-latest, chunked)...")
    # No explicit dates: services.get_ndvi_summary's own defaults already
    # cover 2018-01-01 through "today minus 120 days" (ORNL's processing
    # lag margin), which is exactly the multi-year history the dashboard's
    # year-over-year chart needs, chunked automatically by fetch_ndvi_timeseries.
    ndvi = await services.get_ndvi_summary(lat, lon)
    ndvi["location"] = {"lat": lat, "lon": lon}
    # "partial" just means some composites were cloud/snow-filtered out of
    # the mean -- normal for any real location, not a failure worth a
    # dashboard warning. Only a genuinely unusable fetch should warn.
    if ndvi["status"] not in ("ok", "partial"):
        warnings.append(f"ndvi: {ndvi.get('message') or ndvi['status']}")
    print(" ", ndvi["status"], "-", len(ndvi["points"]), "points")

    soil_layers = soil["layers"] if soil["status"] == "ok" else None

    print("Scoring rotations...")
    rotations_raw = score_all_rotations(climatology, soil_layers, DEMO_PRIORITIES, DEMO_CURRENT_CROPS, lat, top_n=10)
    rotations_raw["location"] = {"lat": lat, "lon": lon}
    rotations_raw["priorities"] = DEMO_PRIORITIES
    rotations_raw["source"] = {
        "source": "sky_to_soil_rotation_optimizer",
        "status": "ok" if climatology is not None and soil_layers is not None else "partial",
        "message": "; ".join(warnings) if warnings else None,
        "cache_hit": False,
        "fetched_at": now_iso(),
    }
    print(f"  {rotations_raw['candidates_evaluated']} candidates evaluated")

    print("Stress-testing top rotations...")
    stress_raw = stress_test_rotations(
        climatology, soil_layers, DEMO_PRIORITIES, DEMO_CURRENT_CROPS, lat, 1.5, -15.0, top_n=10
    )
    stress_raw["location"] = {"lat": lat, "lon": lon}
    stress_raw["scenario"] = {"delta_temp_c": 1.5, "rainfall_change_pct": -15.0}
    stress_raw["source"] = rotations_raw["source"]

    print("Precomputing per-crop climate detail for AI Agronomist (all crops)...")
    crop_lookup = crops_by_id()
    advisor_crop_detail = {
        crop["id"]: advisor_facts.compute_crop_climate_detail(crop, climatology, lat) for crop in load_crops()
    }

    print("Precomputing AI Agronomist explanation for the #1 rotation (en + ur)...")
    climate_block = (
        {"baseline": climate["baseline"], "recent": climate["recent"], "deltas": climate["deltas"], "trends": climate["trends"]}
        if climate
        else None
    )
    top_rotation = rotations_raw["top"][0]
    top_rotation_crop_ids = {slot: cid for slot, cid in top_rotation["rotation"].items() if cid}
    top_stress_entry = advisor_facts.find_stress_entry(stress_raw, top_rotation["rotation"])
    bundle = {
        "location": {"lat": lat, "lon": lon},
        "current_crops": DEMO_CURRENT_CROPS,
        "rotation_entry": top_rotation,
        "stress_entry": top_stress_entry,
        "climate_block": climate_block,
        "soil_layers": soil_layers,
        "per_crop_detail": {cid: advisor_crop_detail[cid] for cid in set(top_rotation_crop_ids.values()) if cid in advisor_crop_detail},
        "data_sources": [
            {"source": "nasa_power", "status": "ok" if climate_block else "unavailable"},
            {"source": "isric_soilgrids", "status": soil["status"]},
            {"source": "sky_to_soil_rotation_optimizer", "status": "ok"},
        ],
    }

    advisor_explain = {"top_0": {}}
    for language in ("en", "ur"):
        result = await run_explain(bundle, DEMO_CURRENT_CROPS, language)
        advisor_explain["top_0"][language] = _explain_payload(result, language)
        print(f"  explain[{language}]: model_used={result.get('model_used')} verified={result.get('verified')}")

    print("Precomputing AI Agronomist chat answers for sample questions (en + ur)...")
    advisor_chat = {"en": [], "ur": []}
    for language, questions in DEMO_CHAT_QUESTIONS.items():
        for question in questions:
            result = await run_chat(bundle, DEMO_CURRENT_CROPS, language, question)
            advisor_chat[language].append({"question": question, "response": _chat_payload(result, language)})
            print(f"  chat[{language}] '{question[:40]}...': model_used={result.get('model_used')} verified={result.get('verified')}")

    demo_analysis = {
        "location": {"lat": lat, "lon": lon},
        "generated_at": now_iso(),
        "climate": climate,
        "soil": soil,
        "ndvi": ndvi,
        "rotations": rotations_raw,
        "stress_test": stress_raw,
        "advisor_crop_detail": advisor_crop_detail,
        "advisor_explain": advisor_explain,
        "advisor_chat": advisor_chat,
        "warnings": warnings,
    }

    DEMO_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DEMO_FILE, "w", encoding="utf-8") as f:
        json.dump(demo_analysis, f, indent=2)

    print(f"\nWrote {DEMO_FILE}")
    print("Warnings:", warnings or "none")


if __name__ == "__main__":
    asyncio.run(main())
