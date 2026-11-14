# Sky-to-Soil frontend

Next.js (App Router) + TypeScript + Tailwind CSS v4 + shadcn/ui + MapLibre
GL + Recharts. Built against `../docs/api_contract.md` for the NASA Space
Apps 2026 "Field Shift" challenge.

## Stack

- **Next.js 16** (App Router, Turbopack) + **React 19** + **TypeScript**
- **Tailwind CSS v4** with an earth-tone design system (soil brown / crop
  green / sky blue), light & dark mode via `next-themes`
- **shadcn/ui** (Base UI primitives) — `components.json` has `"rtl": true`,
  so generated components use logical CSS properties (`ms-`/`me-`,
  `start`/`end`) that flip automatically for Urdu
- **MapLibre GL** for the location picker (uses the key-free MapLibre demo
  vector style — no Mapbox/MapTiler API key needed)
- **Recharts** for climate/NDVI charts
- **Zustand** for the farm-setup store (persisted to `localStorage`) and the
  shared farm-analysis cache
- **jsPDF** for the "Download farm plan" export
- A small custom i18n layer (`src/i18n/`) for English + Urdu (RTL), rather
  than a routing-based i18n framework — simpler for a two-locale, no-SEO-url
  requirement

## Run locally

```bash
npm install
cp .env.example .env.local
npm run dev
```

Open `http://localhost:3000`.

### Mock vs. live backend

`.env.local`:

```
NEXT_PUBLIC_USE_MOCK=true          # true = use frozen demo data, no backend needed
NEXT_PUBLIC_API_URL=http://localhost:8000
```

With `NEXT_PUBLIC_USE_MOCK=true` (the default), every API call in
`src/lib/api-client.ts` is served from `src/mocks/` — a real frozen
response captured from the live backend for a farm near Faisalabad,
Pakistan (see `backend/app/data/demo_analysis.json`, copied here). This
lets the whole app run and demo with zero backend.

Set `NEXT_PUBLIC_USE_MOCK=false` and point `NEXT_PUBLIC_API_URL` at a
running `sky-to-soil` backend (see `../backend/README.md`) to use live data.
The app's own `/setup` → `/dashboard` → `/rotations` flow works identically
either way; only `src/lib/api-client.ts` branches on the flag.

## Scripts

```bash
npm run dev      # dev server (Turbopack)
npm run build    # production build
npm run start    # run the production build
npm run lint     # ESLint (zero errors/warnings as of this build)
```

## Project structure

```
src/
  app/                   Routes: / (landing), /setup, /dashboard, /rotations
  components/
    landing/              Hero, how-it-works, NASA data section, CTA
    setup/                4-step wizard: location, soil, crops, priorities
    dashboard/            KPI cards, climate/NDVI charts, soil profile
    rotations/            Rotation cards, timeline, radar/bars, compare dialog
    agronomist/           Placeholder AI agronomist panel (chat UI, not wired)
    export/                PDF "Download farm plan" button
    shared/                Empty/error states, skeletons, map picker
    layout/                Navbar, footer
    ui/                    shadcn/ui components
  hooks/                  use-farm-analysis, use-crops
  lib/                    api-client (mock/live switch), farm-store, pdf-export, geocode, crop-meta
  i18n/                   en.ts / ur.ts dictionaries + I18nProvider
  mocks/                  Frozen demo data (copied from backend/app/data/)
  types/api.ts            TypeScript mirror of backend/app/schemas.py
```

## Design notes / known adaptations

- **"Monthly" and "yearly trend" charts**: the backend's `/climate`
  response gives baseline-vs-recent period averages (not a monthly or
  per-year time series) plus Mann-Kendall trend *metadata* (direction,
  p-value, Sen's slope) — not raw annual values. The dashboard charts were
  adapted to what the contract actually returns: seasonal "then vs. now"
  bar charts, and a "climate trend signals" list rendering the real
  Mann-Kendall results, rather than fabricating a yearly line series the
  API doesn't provide.
- **PDF export is English-only.** jsPDF's built-in fonts have no Arabic-script
  shaping (no Nastaliq joining for Urdu), so an Urdu PDF would render as
  disconnected glyphs. All on-screen UI is fully bilingual; the exported
  PDF is English regardless of the active site language.
- **Crop names and AI-generated text (reasons/warnings) stay in English**
  even in Urdu mode — those strings come from the backend at request time,
  not from the frontend's dictionary. Translating that dynamic content is
  the designed job of the (currently placeholder) AI agronomist panel once
  it's wired to a real model.
- **RTL**: toggling language sets `dir="rtl"`/`lang="ur"` on `<html>` and
  switches to Noto Nastaliq Urdu. shadcn components were generated with
  `"rtl": true` in `components.json`, so spacing/alignment utilities are
  logical (`ms-`, `me-`, `start`, `end`) and flip automatically — run
  `npx shadcn@latest migrate rtl` again after adding new components if any
  hardcoded `ml-`/`mr-`/`left-`/`right-` slips in.

## Deploying to Vercel

1. Push this repo (or just `frontend/`) to GitHub.
2. In Vercel: **New Project** → import the repo → set **Root Directory**
   to `frontend` (since this is a monorepo with `backend/` alongside).
3. Framework preset: Next.js (auto-detected).
4. Environment variables (Project Settings → Environment Variables):
   - `NEXT_PUBLIC_API_URL` — your deployed backend URL (e.g. the Render
     service from `render.yaml`)
   - `NEXT_PUBLIC_USE_MOCK` — `false` once the backend is live; leave
     `true` to ship a working demo before the backend is deployed
5. Deploy. The backend's CORS config already allows any `https://*.vercel.app`
   origin plus `http://localhost:3000`, so no backend changes are needed for
   a standard Vercel deployment.

```bash
# Or from the CLI, run from frontend/:
npm i -g vercel
vercel          # preview deploy
vercel --prod   # production deploy
```
