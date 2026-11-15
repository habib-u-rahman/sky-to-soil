/**
 * Mock data layer. Sliced from a REAL frozen backend response
 * (backend/app/data/demo_analysis.json, generated against the live NASA
 * POWER / ORNL DAAC MODIS / ISRIC SoilGrids APIs for a farm near
 * Faisalabad, Pakistan) so the mock mode shows authentic numbers, not
 * placeholders. Re-copy that file here if the backend demo data changes.
 */
import type {
  AdvisorChatResponse,
  AdvisorExplainResponse,
  AdvisorLanguage,
  ClimateShiftResponse,
  CropProfile,
  CropsListResponse,
  FarmAnalyzeResponse,
  HealthResponse,
  NdviSummaryResponse,
  RotationsScoreResponse,
  RotationsStressTestResponse,
  SoilPresetsResponse,
  SoilProfileResponse,
} from "@/types/api";
import demoAnalysisRaw from "./demo_analysis.json";
import cropsRaw from "./crops.json";

interface DemoAnalysisRaw extends FarmAnalyzeResponse {
  advisor_explain?: Record<string, Partial<Record<AdvisorLanguage, AdvisorExplainResponse>>>;
  advisor_chat?: Record<AdvisorLanguage, { question: string; response: AdvisorChatResponse }[]>;
}

const demoAnalysis = demoAnalysisRaw as unknown as DemoAnalysisRaw;
const crops = cropsRaw as unknown as CropProfile[];

/** Precomputed AI Agronomist output for the #1 rotation ("top_0"), bundled
 * straight into the frontend build. This is what lets the agronomist panel
 * answer instantly for the demo farm even when the backend (and therefore
 * the live Groq call) is unreachable -- see lib/api-client.ts's demo-mode
 * fallback. Any rotation other than "top_0", or any chat question not in
 * the precomputed list below, has no offline answer; the backend has to
 * actually be reachable for those. */
export const mockAdvisorExplainTop0 = demoAnalysis.advisor_explain?.top_0 ?? {};

export const mockAdvisorChatByQuestion = demoAnalysis.advisor_chat ?? ({} as Record<AdvisorLanguage, { question: string; response: AdvisorChatResponse }[]>);

export const mockHealth: HealthResponse = {
  status: "ok",
  service: "sky-to-soil-backend",
  version: "0.1.0",
  time: demoAnalysis.generated_at,
};

export const mockFarmAnalyze: FarmAnalyzeResponse = demoAnalysis;

export const mockClimate: ClimateShiftResponse = demoAnalysis.climate as ClimateShiftResponse;

export const mockSoil: SoilProfileResponse = demoAnalysis.soil as SoilProfileResponse;

export const mockNdvi: NdviSummaryResponse = demoAnalysis.ndvi as NdviSummaryResponse;

export const mockRotationsScore: RotationsScoreResponse = demoAnalysis.rotations as RotationsScoreResponse;

export const mockStressTest: RotationsStressTestResponse =
  demoAnalysis.stress_test as RotationsStressTestResponse;

export const mockCrops: CropsListResponse = {
  crops,
  count: crops.length,
};

// Mirrors backend/app/routers/soil.py's SOIL_PRESETS table.
export const mockSoilPresets: SoilPresetsResponse = {
  presets: [
    { texture: "sand", phh2o: 6.5, clay_pct: 5.0, sand_pct: 88.0, silt_pct: 7.0, soc_g_kg: 5.0, nitrogen_g_kg: 0.3, cec_cmol_kg: 5.0 },
    { texture: "sandy_loam", phh2o: 6.5, clay_pct: 12.0, sand_pct: 63.0, silt_pct: 25.0, soc_g_kg: 8.0, nitrogen_g_kg: 0.5, cec_cmol_kg: 9.0 },
    { texture: "loam", phh2o: 6.8, clay_pct: 20.0, sand_pct: 40.0, silt_pct: 40.0, soc_g_kg: 15.0, nitrogen_g_kg: 1.0, cec_cmol_kg: 16.0 },
    { texture: "silt_loam", phh2o: 6.8, clay_pct: 15.0, sand_pct: 20.0, silt_pct: 65.0, soc_g_kg: 15.0, nitrogen_g_kg: 1.0, cec_cmol_kg: 17.0 },
    { texture: "clay_loam", phh2o: 7.0, clay_pct: 32.0, sand_pct: 30.0, silt_pct: 38.0, soc_g_kg: 18.0, nitrogen_g_kg: 1.2, cec_cmol_kg: 25.0 },
    { texture: "clay", phh2o: 7.2, clay_pct: 50.0, sand_pct: 20.0, silt_pct: 30.0, soc_g_kg: 20.0, nitrogen_g_kg: 1.3, cec_cmol_kg: 35.0 },
  ],
  source: {
    source: "usda_fao_texture_class_typical_values",
    status: "ok",
    message: "Approximate midpoints per USDA-NRCS soil texture class definitions.",
    cache_hit: false,
    fetched_at: null,
  },
};
