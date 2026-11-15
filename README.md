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

## References and data

Every number this app shows traces back to one of the sources below.

**Earth observation & soil data**
- [NASA POWER](https://power.larc.nasa.gov/) -- daily agroclimatology
  (temperature, rainfall, root-zone wetness, humidity, wind, solar
  radiation), 2001-present. NASA data; public domain / no restriction on
  use for this type of data product.
- [ORNL DAAC MODIS MOD13Q1](https://modis.ornl.gov/) -- 250 m, 16-day
  vegetation index (NDVI) composites via the ORNL DAAC MODIS/VIIRS web
  service. NASA data; public domain.
- [ISRIC SoilGrids](https://soilgrids.org/) -- global gridded soil
  property predictions (pH, texture, organic carbon, nitrogen, CEC) at
  multiple depths. Data licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- [OpenStreetMap Nominatim](https://nominatim.org/) -- place-name search
  used in the farm-setup location picker, and OpenStreetMap map tiles
  used for the location map. Data © OpenStreetMap contributors, licensed
  [ODbL](https://www.openstreetmap.org/copyright); used per Nominatim's
  and the tile provider's usage policies.

**Agronomic reference data**
- FAO-56 (Allen, Pereira, Raes & Smith, *Crop Evapotranspiration --
  Guidelines for Computing Crop Water Requirements*, FAO Irrigation and
  Drainage Paper 56, 1998) -- crop coefficients (Kc) and reference
  evapotranspiration method used by the water-need calculations.
- FAO conservation agriculture guidance, and the peer-reviewed crop
  physiology sources cited per-field in `backend/app/data/crops.json`
  (heat-stress thresholds, rooting depths, etc.) -- see that file's
  `sources` blocks for the exact citation behind each value.

**Frameworks & libraries**
| Library | Used for | License |
|---|---|---|
| [Next.js](https://nextjs.org/) | Frontend framework | MIT |
| [React](https://react.dev/) | UI library | MIT |
| [FastAPI](https://fastapi.tiangolo.com/) | Backend API framework | MIT |
| [LangGraph](https://github.com/langchain-ai/langgraph) | AI Agronomist pipeline orchestration | MIT |
| [Groq](https://groq.com/) | LLM inference API (`openai/gpt-oss-120b`) | Commercial API service |
| [ReportLab](https://www.reportlab.com/opensource/) | Farm-plan PDF generation | BSD-style (ReportLab open-source license) |
| [shadcn/ui](https://ui.shadcn.com/) | UI components (built on Base UI) | MIT |
| [MapLibre GL JS](https://maplibre.org/) | Interactive location map | BSD-3-Clause |
| [Recharts](https://recharts.org/) | Dashboard charts | MIT |
| [Zustand](https://zustand-demo.pmnd.rs/) | Frontend state management | MIT |

## License

This project is licensed under the MIT License -- see `LICENSE`.
