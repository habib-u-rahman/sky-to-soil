/**
 * Mock data layer. Sliced from a REAL frozen backend response
 * (backend/app/data/demo_analysis.json, generated against the live NASA
 * POWER / ORNL DAAC MODIS / ISRIC SoilGrids APIs for a farm near
 * Faisalabad, Pakistan) so the mock mode shows authentic numbers, not
 * placeholders. Re-copy that file here if the backend demo data changes.
 */
import type {
  ClimateShiftResponse,
  CropProfile,
  CropsListResponse,
  FarmAnalyzeResponse,
  HealthResponse,
  NdviSummaryResponse,
  RotationsScoreResponse,
  RotationsStressTestResponse,
  SoilProfileResponse,
} from "@/types/api";
import demoAnalysisRaw from "./demo_analysis.json";
import cropsRaw from "./crops.json";

const demoAnalysis = demoAnalysisRaw as unknown as FarmAnalyzeResponse;
const crops = cropsRaw as unknown as CropProfile[];

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
