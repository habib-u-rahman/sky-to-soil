"""Evaluates the AI Agronomist's rule-based verifier against real Groq
calls for the demo farm: explain for the top 5 rotations x 2 languages (10
runs) + 10 fixed chat questions (5 English, 5 Urdu). Reports the verify
pass rate *before* any rewrite (first attempt) and *after* the one allowed
rewrite + deterministic fallback (final), plus how often the fallback
template had to be used at all.

These are the real numbers to quote for the pitch -- run it fresh rather
than trusting a stale copy:

    python -m scripts.eval_advisor   (from the backend/ directory)

Writes backend/results/advisor_eval.json.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app import services
from app.advisor.facts import compute_crop_climate_detail, find_stress_entry
from app.advisor.graph import run_chat, run_explain
from app.core.demo import DEMO_LOCATION
from app.data.crop_repo import crops_by_id
from app.science.climatology import build_doy_climatology
from app.science.rotation_engine import score_all_rotations, stress_test_rotations
from app.scripts.build_demo import DEMO_CURRENT_CROPS, DEMO_PRIORITIES

RESULTS_PATH = Path(__file__).resolve().parent.parent / "results" / "advisor_eval.json"

CHAT_QUESTIONS = [
    ("en", "Why was this rotation recommended for my farm?"),
    ("en", "How much water deficit does the main crop have in this rotation?"),
    ("en", "Will I definitely make more money by switching to this rotation?"),
    ("en", "What is my soil texture and pH?"),
    ("en", "Is there a risk of heat stress for any crop in this rotation?"),
    ("ur", "یہ ترتیب میرے فارم کے لیے کیوں تجویز کی گئی؟"),
    ("ur", "اس ترتیب میں مجھے کس بات کا خیال رکھنا چاہیے؟"),
    ("ur", "میری زمین کی مٹی کی قسم اور پی ایچ کیا ہے؟"),
    ("ur", "کیا موسمیاتی تبدیلی میرے علاقے میں بارش کو متاثر کر رہی ہے؟"),
    ("ur", "کیا یہ ترتیب فصل کی قیمت بڑھا دے گی؟"),
]


async def _build_static_inputs():
    lat, lon = DEMO_LOCATION["lat"], DEMO_LOCATION["lon"]
    climate_raw = await services.get_climate_shift(lat, lon)
    soil = await services.get_soil_profile(lat, lon)

    climatology = None
    climate_block = None
    if not climate_raw.get("error"):
        climatology = build_doy_climatology(climate_raw["_power_series"], recent_start_year=2013)
        climate_block = {
            "baseline": climate_raw["baseline"],
            "recent": climate_raw["recent"],
            "deltas": climate_raw["deltas"],
            "trends": climate_raw["trends"],
        }
    soil_layers = soil["layers"] if soil["status"] == "ok" else None

    rotations = score_all_rotations(climatology, soil_layers, DEMO_PRIORITIES, DEMO_CURRENT_CROPS, lat, top_n=5)
    stress = stress_test_rotations(climatology, soil_layers, DEMO_PRIORITIES, DEMO_CURRENT_CROPS, lat, 1.5, -15.0, top_n=5)

    data_sources = [
        {"source": "nasa_power", "status": "ok" if climate_block else "unavailable"},
        {"source": "isric_soilgrids", "status": soil["status"]},
        {"source": "sky_to_soil_rotation_optimizer", "status": "ok"},
    ]
    return lat, lon, climatology, climate_block, soil_layers, rotations, stress, data_sources


def _make_bundle(rotation_entry, lat, lon, climatology, climate_block, soil_layers, stress, data_sources) -> dict:
    crop_lookup = crops_by_id()
    rotation_crop_ids = {slot: cid for slot, cid in rotation_entry["rotation"].items() if cid}
    per_crop_detail = {
        cid: compute_crop_climate_detail(crop_lookup[cid], climatology, lat)
        for cid in set(rotation_crop_ids.values())
        if cid in crop_lookup
    }
    stress_entry = find_stress_entry(stress, rotation_entry["rotation"])
    return {
        "location": {"lat": lat, "lon": lon},
        "current_crops": DEMO_CURRENT_CROPS,
        "rotation_entry": rotation_entry,
        "stress_entry": stress_entry,
        "climate_block": climate_block,
        "soil_layers": soil_layers,
        "per_crop_detail": per_crop_detail,
        "data_sources": data_sources,
    }


def _run_record(result: dict, extra: dict) -> dict:
    return {
        **extra,
        "first_attempt_verified": result.get("first_attempt_verified", False),
        "final_verified": result.get("verified", False),
        "rewrites_used": result.get("rewrites_used", 0),
        "used_fallback": result.get("model_used") == "fallback_template",
        "model_used": result.get("model_used"),
        "issues": result.get("issues", []),
    }


async def main():
    print(f"Building rotation candidates for the demo farm {DEMO_LOCATION}...")
    lat, lon, climatology, climate_block, soil_layers, rotations, stress, data_sources = await _build_static_inputs()

    explain_runs = []
    print("Running /advisor/explain for top 5 rotations x 2 languages (10 runs)...")
    for i, rotation_entry in enumerate(rotations["top"][:5]):
        bundle = _make_bundle(rotation_entry, lat, lon, climatology, climate_block, soil_layers, stress, data_sources)
        for language in ("en", "ur"):
            result = await run_explain(bundle, DEMO_CURRENT_CROPS, language)
            record = _run_record(result, {"rotation_index": i, "rotation": rotation_entry["rotation"], "language": language})
            explain_runs.append(record)
            print(
                f"  explain rotation#{i} [{language}]: first_pass={record['first_attempt_verified']} "
                f"final={record['final_verified']} model={record['model_used']}"
            )

    chat_runs = []
    print("Running /advisor/chat for 10 sample questions...")
    chat_bundle = _make_bundle(rotations["top"][0], lat, lon, climatology, climate_block, soil_layers, stress, data_sources)
    for language, question in CHAT_QUESTIONS:
        result = await run_chat(chat_bundle, DEMO_CURRENT_CROPS, language, question)
        record = _run_record(result, {"question": question, "language": language, "answerable": result.get("answerable", False)})
        chat_runs.append(record)
        print(
            f"  chat [{language}] '{question[:30]}...': first_pass={record['first_attempt_verified']} "
            f"final={record['final_verified']} model={record['model_used']}"
        )

    all_runs = explain_runs + chat_runs
    n = len(all_runs)
    summary = {
        "n_explain_runs": len(explain_runs),
        "n_chat_runs": len(chat_runs),
        "n_total_runs": n,
        "verify_pass_rate_before_rewrite_pct": round(100 * sum(r["first_attempt_verified"] for r in all_runs) / n, 1),
        "verify_pass_rate_after_rewrite_and_fallback_pct": round(100 * sum(r["final_verified"] for r in all_runs) / n, 1),
        "pct_runs_that_needed_fallback_template": round(100 * sum(r["used_fallback"] for r in all_runs) / n, 1),
    }

    output = {"summary": summary, "explain_runs": explain_runs, "chat_runs": chat_runs}

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("\n=== SUMMARY ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print(f"\nWrote {RESULTS_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
