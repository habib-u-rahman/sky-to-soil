# Sky-to-Soil backend

FastAPI service that turns NASA Earth observations + local soil data + a
14-crop agronomic knowledge base into crop-rotation recommendations. Built
for the NASA Space Apps 2026 "Field Shift" challenge.

See `../docs/api_contract.md` for the full endpoint contract and
`../docs/samples/` for example responses. Live interactive docs are at
`/docs` once the server is running.

## Setup

Requires Python 3.11+.

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate      # Windows (Git Bash) / macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env                # fill in GROQ_API_KEY if you use it
```

## Run

```bash
uvicorn app.main:app --reload
```

Server starts at `http://localhost:8000`. Try:

```bash
curl http://localhost:8000/health
curl "http://localhost:8000/crops"
curl "http://localhost:8000/climate?lat=31.42&lon=73.08"
curl "http://localhost:8000/farm/analyze?demo=true" -X POST -H "Content-Type: application/json" -d '{"location":{"lat":31.42,"lon":73.08}}'
```

## Tests

```bash
pytest
```

125+ tests cover the science modules (climate trend stats, ET0, crop water
need, heat stress, soil suitability, the rotation optimizer) with synthetic
data, plus API-level tests with upstream clients mocked (fast, offline).
Real-API verification was done manually against the live NASA POWER, ORNL
DAAC MODIS, and ISRIC SoilGrids endpoints -- see the module docstrings in
`app/clients/` for exactly what was checked and when. The AI Agronomist
(`app/advisor/`) has its own test files (`tests/test_advisor_*.py`) covering
the rule-based verifier, KB retrieval, facts assembly, the fallback
template, the LangGraph pipeline (Groq mocked), and the model-selection
logic -- plus full API-level tests for `/advisor/explain`, `/advisor/chat`,
and `/report/pdf` in both demo (real frozen data, no mocking needed) and
live (upstream + Groq mocked) modes.

## Demo mode

`?demo=true` on any endpoint (GET query param or, for POST endpoints, also
a query param, e.g. `POST /farm/analyze?demo=true`) returns a frozen
analysis for a farm near Faisalabad, Pakistan (31.42 N, 73.08 E) with zero
network access -- this now includes AI Agronomist output (a precomputed
explanation for the #1 rotation in English + Urdu, and answers to 5 sample
chat questions per language; any other demo-mode request still works
offline via the deterministic fallback template, see `app/advisor/`).
Rebuild it after changing science/data/advisor code with:

```bash
python -m app.scripts.build_demo
```

This writes `app/data/demo_analysis.json` and makes a handful of live Groq
calls to precompute the advisor cache, so `GROQ_API_KEY` must be set in
`.env` when *regenerating* this file (not needed just to serve `?demo=true`
afterwards).

## AI Agronomist

`app/advisor/` is a LangGraph pipeline over Groq (`openai/gpt-oss-120b`,
with a fallback model) that explains rotation recommendations and answers
farm-specific questions, restricted to a compact `facts` object and a small
curated knowledge base (`data/agronomy_kb.json`), and checked by a
rule-based (no-LLM) verifier before being returned. See
`docs/api_contract.md` for the `/advisor/explain` and `/advisor/chat`
contract, and run the real evaluation with:

```bash
python -m scripts.eval_advisor
```

which writes `backend/results/advisor_eval.json` -- the verify pass rate
numbers there are what should be quoted anywhere real numbers are needed
(e.g. a pitch), since they come from live Groq calls, not from the
(already-verified, so not representative of the raw pass rate) frozen demo
cache.

## Project layout

```
backend/
  app/
    main.py              FastAPI app, CORS, router wiring
    schemas.py            Every request/response Pydantic model (the API contract)
    services.py           Combines clients + science modules into endpoint-shaped dicts
    routers/               One file per route group (health, climate, soil, ndvi, crops, rotations, farm, advisor, report)
    clients/               NASA POWER, ORNL MODIS, ISRIC SoilGrids -- async httpx, retries, disk cache
    science/               Climate trend stats, ET0, crop water need, heat stress, soil suitability, rotation engine
    core/                   Settings, disk cache, HTTP retry helper, demo-mode loader
    advisor/                AI Agronomist: Groq client, KB retrieval, facts builder, LangGraph pipeline, rule-based verifier, fallback template
    report/                 reportlab PDF farm-plan builder
    data/
      crops.json            14-crop knowledge base (FAO-56 Kc stages, critical temps, pH/texture, cited sources)
      crop_repo.py           Loads/indexes crops.json
      demo_analysis.json     Frozen demo dataset (generated, see above)
    scripts/
      build_demo.py          Regenerates demo_analysis.json from live data (+ advisor cache)
  data/
    agronomy_kb.json         Curated agronomy knowledge base for the AI Agronomist (FAO-56, conservation ag, legume N, residue/SOM, crop diversity, heat stress, water-saving)
  scripts/
    eval_advisor.py          Real-Groq evaluation of the advisor verifier's pass rate -- writes results/advisor_eval.json
  results/
    advisor_eval.json        Output of eval_advisor.py (generated)
  tests/                    pytest suite (science modules + API + advisor)
  Dockerfile                 Still works for local Docker use; render.yaml no longer uses it (native Python runtime)
  requirements.txt / requirements-dev.txt
```

## Known live-data caveats (verified 2026-11-14)

- **NASA POWER** (`power.larc.nasa.gov`): all 8 requested daily parameters
  (T2M_MAX, T2M_MIN, T2M, PRECTOTCORR, GWETROOT, ALLSKY_SFC_SW_DWN, RH2M,
  WS2M) confirmed working with `community=AG`.
- **ORNL DAAC MODIS** (`modis.ornl.gov/rst/api/v1`): confirmed working.
  Two things that aren't obvious from the docs and are handled in
  `app/clients/modis_client.py`: (1) the `subset` endpoint caps requests at
  10 composites (~160 days) and 400s on longer windows -- we chunk and
  fetch concurrently; (2) quality filtering requires a second request for
  the `250m_16_days_pixel_reliability` band.
- **ISRIC SoilGrids** (`rest.isric.org/soilgrids/v2.0`): the endpoint and
  response schema are correct, but the public service was observed to be
  degraded during development -- sometimes a slow hang, sometimes `503`,
  sometimes `200` with every property/depth `null`. We treat all three as
  "soil data unavailable" or "manual_input_needed" and degrade gracefully
  rather than erroring the whole request; `GET /soil` still returns `200`
  with a clear status either way. Retry this later; it may recover.

## Deploying to Render

`render.yaml` at the repo root defines a native Python web service (no
Docker -- `runtime: python`, `pip install -r requirements.txt`, `uvicorn
app.main:app`). Point it at your fork, set `GROQ_API_KEY` in the Render
dashboard (marked `sync: false` in render.yaml so it's not stored in git),
and deploy. Health check path is `/health`.
