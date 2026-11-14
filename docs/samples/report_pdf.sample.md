# `POST /report/pdf` sample output (textual description)

The endpoint returns a binary `application/pdf` body, so there's no JSON
sample here. Generated against the demo farm (`?demo=true`, `top_n=3`),
the report is 3 pages and contains, in order:

1. **Title block**: "Sky-to-Soil Farm Plan", location (31.42, 73.08),
   generation timestamp, current crops (wheat, cotton).
2. **Climate shift summary**: a baseline (2001-2012) vs recent (2013-2025)
   table of mean max/min temperature and kharif/rabi rainfall with deltas,
   plus a line of Mann-Kendall trend results.
3. **Soil**: depth-weighted pH, texture class, clay/sand/silt %, and SOC --
   or, as in the demo farm's case, a note that SoilGrids was unavailable
   and values should be entered manually (pointing at `/soil/presets`).
4. **Top 3 recommended rotations**: a table with each rotation's 4-season
   timeline (Year 1/2 Kharif/Rabi crop names) and its base + priority-
   weighted scores, followed by each rotation's top 2 reasons.
5. **AI Agronomist explanation**: the farmer-facing explanation for
   rotation #1 (always in English in the PDF -- see the known limitation
   noted in `docs/api_contract.md`), followed by a "For extension
   officers" box with the technical note.
6. **Data sources and disclaimer**: NASA POWER / ISRIC SoilGrids / ORNL
   MODIS / the rotation optimizer / the AI explanation's KB sources, and a
   closing disclaimer that this is not a yield/income guarantee and the
   farmer should confirm with their local extension officer.
