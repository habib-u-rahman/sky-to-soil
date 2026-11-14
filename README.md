# Sky-to-Soil

Decision-support tool for the NASA Space Apps 2026 challenge **"Field
Shift: Adapting Farms with NASA Data."** Combines NASA Earth observations
(NASA POWER climate, MODIS NDVI), local soil data (ISRIC SoilGrids), and a
14-crop agronomic knowledge base to help farmers explore 2-year crop
rotations that strengthen soil health and adapt to a shifting climate.

```
sky-to-soil/
  backend/     FastAPI service -- see backend/README.md to run it
  frontend/    (built in a parallel session against docs/api_contract.md)
  docs/
    api_contract.md     Full API contract (request/response shapes)
    samples/             Example JSON response for every endpoint
  render.yaml            Render deployment config for the backend
```

## Quick start

```bash
cd backend
python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Then `curl http://localhost:8000/health`, or browse `/docs` for interactive
OpenAPI docs. `?demo=true` on any endpoint works offline with a frozen
dataset for a farm near Faisalabad, Pakistan.

See `backend/README.md` for full details, test instructions, and notes on
what was verified against the live NASA/ISRIC APIs.
