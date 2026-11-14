# Sky-to-Soil backend API contract

Base URL (local dev): `http://localhost:8000`
All request/response bodies are JSON. All endpoints also accept a `demo=true`
query parameter, which short-circuits every live fetch and returns the frozen
Faisalabad, Pakistan (31.42 N, 73.08 E) demo dataset in
`backend/app/data/demo_analysis.json` — this is what powers offline demos.

This document is a human-readable mirror of `backend/app/schemas.py`
(Pydantic models, which FastAPI also turns into live OpenAPI docs at
`/docs`). If the two ever disagree, `schemas.py` wins — update this file
to match. Sample payloads for every endpoint live in `docs/samples/`.

CORS: `http://localhost:3000` and any `https://*.vercel.app` origin are
allowed by default; see `EXTRA_CORS_ORIGINS` in `backend/.env.example` to add
more.

## Status conventions

Every data block that comes from an external source carries a `source`
object:

```json
{"source": "nasa_power", "status": "ok", "message": null, "cache_hit": false, "fetched_at": "2026-11-14T06:00:00Z"}
```

`status` is one of:
- `ok` — data returned normally.
- `partial` — some but not all of the requested data came back (e.g. one
  SoilGrids depth layer was null).
- `unavailable` — the source could not be reached after retries.
- `manual_input_needed` — the source responded but had no usable value for
  this location (e.g. SoilGrids returning null); the frontend should offer
  manual entry fields.
- `error` — an unexpected error occurred; `message` has details.

`/farm/analyze` never fails outright because one sub-source failed: it
returns whatever it could gather and lists problems in `warnings`. The
single-resource GETs (`/soil`, `/ndvi`) follow the same rule and always
return `200` with a status field, even when their source is fully
unavailable. `/climate` is the one exception: its response schema requires
a fully-populated baseline/recent comparison, so if NASA POWER cannot be
reached at all, it returns `502` with a `detail` message instead of a
partially-null body.

---

## `GET /health`

No params.

```json
{"status": "ok", "service": "sky-to-soil-backend", "version": "0.1.0", "time": "2026-11-14T06:00:00Z"}
```

---

## `GET /climate`

Query params: `lat` (float, required), `lon` (float, required),
`start_year` (int, optional, default 2001), `end_year` (int, optional,
default = latest full calendar year), `demo` (bool, optional).

Compares a baseline period (`start_year`..2012) against a recent period
(2013..`end_year`) using NASA POWER daily data. Returns per-period means,
per-season hot-day counts, per-season rainfall, mean root-zone wetness, and
Mann-Kendall trend + Sen's slope for each annual series
(`mean_tmax_c`, `mean_tmin_c`, `kharif_rainfall_mm`, `rabi_rainfall_mm`,
`root_zone_wetness`).

Seasons default to `kharif` = May-Oct, `rabi` = Nov-Apr (configurable via
`POST /rotations/score` and `/farm/analyze` bodies for other regions; the GET
endpoint uses the default).

See `docs/samples/climate.sample.json`. Shape: `ClimateShiftResponse` in
`schemas.py`.

---

## `GET /soil/presets`

No params. Returns typical representative soil property values for 6 USDA
texture classes (`sand`, `sandy_loam`, `loam`, `silt_loam`, `clay_loam`,
`clay`) so the frontend can auto-fill soil inputs when ISRIC SoilGrids is
unavailable. These are illustrative midpoints, not location-specific --
`source.message` carries the citation.

See `docs/samples/soil_presets.sample.json`. Shape: `SoilPresetsResponse`.

---

## `GET /soil`

Query params: `lat`, `lon` (required), `demo` (optional).

Fetches SoilGrids (ISRIC) phh2o, clay, sand, silt, soc, nitrogen, cec at
0-5, 5-15, 15-30 cm. **Known issue (verified 2026-11-14): the public ISRIC
SoilGrids REST API currently returns `null` for every property/depth we
tested, at multiple real coordinates, while still returning HTTP 200** —
this looks like a live ISRIC backend data outage, not a bug in our request.
The client detects an all-null response and returns
`status: "manual_input_needed"` with empty layer values so the frontend can
render manual-entry fields instead of blank numbers.

See `docs/samples/soil.sample.json`. Shape: `SoilProfileResponse`.

---

## `GET /ndvi`

Query params: `lat`, `lon` (required), `start_date` (YYYY-MM-DD, optional,
default 2 years before latest available), `end_date` (optional, default
latest available), `demo` (optional).

Fetches MOD13Q1 250 m 16-day NDVI from the ORNL DAAC MODIS web service,
applies the 0.0001 scale factor, and filters by
`250m_16_days_pixel_reliability` (0 = good, 1 = marginal, 2 = snow/ice,
3 = cloudy; only 0/1 are `usable: true`). Returns the full time series plus
a quality-filtered mean.

See `docs/samples/ndvi.sample.json`. Shape: `NdviSummaryResponse`.

---

## `GET /crops`

No params. Returns the full backend/data/crops.json knowledge base
(~14 crops) validated against `CropProfile`.

See `docs/samples/crops.sample.json`. Shape: `CropsListResponse`.

---

## `POST /rotations/score`

Body: `RotationScoreRequest`

```json
{
  "location": {"lat": 31.42, "lon": 73.08},
  "current_crops": ["wheat", "cotton"],
  "priorities": {"save_water": 0.3, "build_soil": 0.3, "lower_climate_risk": 0.2, "stay_close_to_current": 0.2},
  "top_n": 10
}
```

Generates every valid 2-year / 4-season rotation (`Y1_kharif`, `Y1_rabi`,
`Y2_kharif`, `Y2_rabi`; each slot is a crop id matching the slot's season,
or `null` for fallow/cover crop), scores each on four 0-100 sub-scores
(`water_fit`, `heat_risk`, `soil_health`, `soil_suitability`) using live
climate+soil data for `location`, combines sub-scores with the farmer's
priority weights into `priority_weighted_score_0_100`, and returns the top
N plus the Pareto-optimal set (rotations not dominated on all four
sub-scores by any other candidate).

See `docs/samples/rotations_score.sample.json`. Shape:
`RotationsScoreResponse`.

---

## `POST /rotations/stress-test`

Body: `StressTestRequest` — same shape as the score request plus an
optional `scenario` (`delta_temp_c` default `+1.5`, `rainfall_change_pct`
default `-15`).

Re-scores the same candidate rotations under the shifted climate and
reports `resilience_score_0_100 = 100 - (baseline_score - stressed_score)`,
clamped to `[0, 100]`.

See `docs/samples/rotations_stress_test.sample.json`. Shape:
`RotationsStressTestResponse`.

---

## `POST /farm/analyze`

Body: `FarmAnalyzeRequest` (location, current_crops, priorities,
optional season_config, `include_stress_test` default `true`, `top_n`
default 10).

One-call convenience endpoint: runs climate + soil + NDVI fetches
concurrently, then scores rotations (and stress-tests them unless
`include_stress_test` is `false`). If any one of climate/soil/ndvi fails,
the corresponding field is `null` and a human-readable line is appended to
`warnings` — the call still returns `200` with everything else filled in.
Rotation scoring falls back to defaults (skip soil-suitability weighting,
etc.) when a sub-source is missing, and that fallback is also noted in
`warnings`.

See `docs/samples/farm_analyze.sample.json`. Shape: `FarmAnalyzeResponse`.

---

## AI Agronomist (`/advisor/*`)

Backed by `backend/app/advisor/` -- a LangGraph pipeline (`collect_facts ->
retrieve -> write -> verify -> rewrite (once, if verify fails) ->
fallback_template (if still failing)`) over Groq (`openai/gpt-oss-120b`,
falling back to one other model if the primary call fails; `temperature=0`).

**The model is only ever shown a compact `facts` object** derived from the
farm analysis and the selected rotation -- climate-shift deltas, soil
values, per-crop water deficit / heat-stress days, rotation sub-scores, the
stress-test result (if available), and the data sources actually used. It
is never given raw upstream payloads, and the response schema exposes that
same `facts_used` object plus `kb_sources` so the frontend can render
"verified" badges and citations.

`verify` is pure rule-based Python (no LLM): every number in the generated
text must match a `facts_used` value (rounding-tolerant; handles
Urdu/Arabic-Indic digits), every crop named must be in the rotation or
`current_crops`, every source cited must be a retrieved KB source or a data
source actually used, and yield/profit guarantee language is rejected. If
the model's first attempt fails, it gets one rewrite with the specific
issues listed; if that also fails, a deterministic, LLM-free template
(`fallback_template.py`) built directly from `facts` is returned instead --
this is also what demo mode uses, since the knowledge-base retrieval is a
local TF-IDF ranker with no network dependency.

Both endpoints take an `analysis` body field -- the full `FarmAnalyzeResponse`
payload as returned by `POST /farm/analyze` -- and a `rotation_id` (e.g.
`"top_0"`, `"pareto_1"`) selecting which scored rotation to ground the
answer in. `analysis` is not required when `?demo=true` is set; demo mode
instead uses the frozen demo farm's analysis and, for the default
`rotation_id` (`"top_0"`) and a small set of precomputed sample questions,
returns a cached response with zero network calls. Any other demo-mode
request still works offline via the deterministic fallback template.

### `POST /advisor/explain`

Body: `AdvisorExplainRequest` (`analysis`, `rotation_id`, `current_crops`,
`language`: `"en"` | `"ur"`).

```json
{
  "rotation_id": "top_0",
  "current_crops": ["wheat", "cotton"],
  "language": "en",
  "analysis": { "...": "a POST /farm/analyze response" }
}
```

Returns a farmer-friendly explanation (why this rotation, what's changing
in their climate, what to watch out for, 3 practical tips) plus a short
English technical note for extension officers.

See `docs/samples/advisor_explain.sample.json`. Shape: `AdvisorExplainResponse`.

### `POST /advisor/chat`

Body: `AdvisorChatRequest` (`analysis`, `rotation_id` optional, defaults to
`"top_0"`, `current_crops`, `question`, `language`).

Answers questions about THIS farm only, grounded strictly in `facts` + the
knowledge base. If the question can't be honestly answered from what's
available, `answerable: false` and the answer says so instead of guessing.

See `docs/samples/advisor_chat.sample.json`. Shape: `AdvisorChatResponse`.

---

## `POST /report/pdf`

Body: `ReportPdfRequest` (`analysis`, `current_crops`, `language` --
currently rendered in English only regardless of this field, see note
below --, `top_n` default 3).

Returns a 2-3 page PDF (`application/pdf`, `Content-Disposition: attachment;
filename=sky2soil_farm_plan.pdf`) covering: farm location, climate-shift
summary, soil, the top N scored rotations with their 4-season timelines and
scores, the AI Agronomist explanation for the #1 rotation, and data sources
+ disclaimer. Built with `reportlab` in `backend/app/report/pdf_builder.py`.

Like the advisor endpoints, `analysis` is required unless `?demo=true`.
**Known limitation:** the PDF always renders in English -- reportlab's base
fonts don't shape/reorder Urdu (Nastaliq) script correctly without extra
font + bidi-reshaping dependencies, so an Urdu PDF isn't offered yet rather
than shipping a garbled one.

No sample JSON (binary response) -- see `docs/samples/report_pdf.sample.md`
for a textual description of a generated report's contents.

---

## Demo mode

Any endpoint above accepts `?demo=true` (or, for POST endpoints, a body
with `"demo": true` is NOT required — demo mode is a query param on all
routes, including POST, e.g. `POST /farm/analyze?demo=true`). This returns
pre-baked data for the Faisalabad demo farm regardless of the
lat/lon/body supplied, so the frontend always has something to show with
zero network dependency. Generate/refresh the frozen file with:

```
python -m app.scripts.build_demo
```

which writes `backend/app/data/demo_analysis.json`. This now also makes a
handful of live Groq calls to precompute the AI Agronomist's explanation
for the #1 rotation (English + Urdu) and answers to 5 sample chat questions
per language, so `GROQ_API_KEY` must be set in `.env` when *regenerating*
the demo file -- but not for *serving* `?demo=true` afterwards, which only
reads the frozen JSON.
