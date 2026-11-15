/**
 * TypeScript mirror of backend/app/schemas.py (the Sky-to-Soil API contract).
 * Keep in sync with docs/api_contract.md — if the backend schema changes,
 * update these types in the same change.
 */

export type DataStatus = "ok" | "partial" | "unavailable" | "manual_input_needed" | "error";

export interface SourceMeta {
  source: string;
  status: DataStatus;
  message: string | null;
  cache_hit: boolean;
  fetched_at: string | null;
}

export interface Location {
  lat: number;
  lon: number;
}

export interface SeasonWindow {
  name: string;
  start_month: number;
  end_month: number;
}

export interface SeasonConfig {
  kharif: SeasonWindow;
  rabi: SeasonWindow;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  time: string;
}

// ---------------------------------------------------------------------------
// Climate
// ---------------------------------------------------------------------------

export interface SeasonalRainfall {
  kharif_mm: number | null;
  rabi_mm: number | null;
}

export interface SeasonalHotDays {
  kharif: number | null;
  rabi: number | null;
}

export interface PeriodClimateStats {
  period_label: string;
  start_year: number;
  end_year: number;
  n_years: number;
  mean_tmax_c: number | null;
  mean_tmin_c: number | null;
  hot_days_gt35_by_season: SeasonalHotDays;
  hot_days_gt40_by_season: SeasonalHotDays;
  seasonal_rainfall_mm: SeasonalRainfall;
  mean_root_zone_wetness: number | null;
}

export interface TrendResult {
  variable: string;
  mk_trend: "increasing" | "decreasing" | "no trend";
  mk_p_value: number | null;
  sen_slope_per_year: number | null;
  significant_at_0_10: boolean;
}

export interface ClimateDeltas {
  mean_tmax_c?: number | null;
  mean_tmin_c?: number | null;
  mean_root_zone_wetness?: number | null;
  kharif_rainfall_mm?: number | null;
  rabi_rainfall_mm?: number | null;
  [key: string]: number | null | undefined;
}

export interface ClimateShiftResponse {
  location: Location;
  baseline: PeriodClimateStats;
  recent: PeriodClimateStats;
  deltas: ClimateDeltas;
  trends: TrendResult[];
  seasons_used: SeasonConfig;
  source: SourceMeta;
}

// ---------------------------------------------------------------------------
// Soil
// ---------------------------------------------------------------------------

export type SoilDepthLabel = "0-5cm" | "5-15cm" | "15-30cm";

export interface SoilDepthLayer {
  depth: SoilDepthLabel;
  phh2o: number | null;
  clay_pct: number | null;
  sand_pct: number | null;
  silt_pct: number | null;
  soc_g_kg: number | null;
  nitrogen_g_kg: number | null;
  cec_cmol_kg: number | null;
}

export interface SoilProfileResponse {
  location: Location;
  layers: SoilDepthLayer[];
  status: DataStatus;
  message: string | null;
  source: SourceMeta;
}

// ---------------------------------------------------------------------------
// NDVI
// ---------------------------------------------------------------------------

export interface NdviPoint {
  modis_date: string;
  calendar_date: string;
  ndvi: number | null;
  quality_code: number | null;
  quality_label: string | null;
  usable: boolean;
}

export interface NdviSummaryResponse {
  location: Location;
  period_start: string;
  period_end: string;
  points: NdviPoint[];
  mean_ndvi_good_quality: number | null;
  pct_usable: number | null;
  status: DataStatus;
  message: string | null;
  source: SourceMeta;
}

// ---------------------------------------------------------------------------
// Crops
// ---------------------------------------------------------------------------

export type Fao56Stage = "initial" | "development" | "mid" | "late";

export interface KcStage {
  stage: Fao56Stage;
  length_days: number;
  kc: number;
}

export interface SourceCitation {
  text: string;
  verify: boolean;
}

export type CropSeason = "kharif" | "rabi" | "either";
export type ResidueLevel = "low" | "medium" | "high";

export interface CropProfile {
  id: string;
  name: string;
  family: string;
  n_fixing: boolean;
  season: CropSeason;
  sowing_window: string;
  duration_days: number;
  kc_stages: KcStage[];
  critical_temp_c: number;
  heat_sensitive_stage: string;
  ph_min: number;
  ph_max: number;
  texture_preference: string[];
  residue_contribution: ResidueLevel;
  rooting_depth_m: number;
  sources: Record<string, SourceCitation>;
}

export interface CropsListResponse {
  crops: CropProfile[];
  count: number;
}

// ---------------------------------------------------------------------------
// Rotations
// ---------------------------------------------------------------------------

export interface Priorities {
  save_water: number;
  build_soil: number;
  lower_climate_risk: number;
  stay_close_to_current: number;
  income_proxy: number | null;
}

export const SEASON_SLOTS = ["Y1_kharif", "Y1_rabi", "Y2_kharif", "Y2_rabi"] as const;
export type SeasonSlot = (typeof SEASON_SLOTS)[number];

export interface RotationPlan {
  Y1_kharif: string | null;
  Y1_rabi: string | null;
  Y2_kharif: string | null;
  Y2_rabi: string | null;
}

export interface RotationSubScores {
  water_fit: number;
  heat_risk: number;
  soil_health: number;
  soil_suitability: number;
}

export interface ScoredRotation {
  rotation: RotationPlan;
  sub_scores: RotationSubScores;
  base_score_0_100: number;
  priority_weighted_score_0_100: number;
  reasons: string[];
  warnings: string[];
}

export interface RotationsScoreResponse {
  location: Location;
  priorities: Priorities;
  candidates_evaluated: number;
  top: ScoredRotation[];
  pareto_optimal: ScoredRotation[];
  source: SourceMeta;
}

export interface StressScenario {
  delta_temp_c: number;
  rainfall_change_pct: number;
}

export interface StressedRotationResult {
  rotation: RotationPlan;
  baseline_score_0_100: number;
  stressed_score_0_100: number;
  score_drop: number;
  resilience_score_0_100: number;
  reasons: string[];
}

export interface RotationsStressTestResponse {
  location: Location;
  scenario: StressScenario;
  results: StressedRotationResult[];
  source: SourceMeta;
}

// ---------------------------------------------------------------------------
// Requests
// ---------------------------------------------------------------------------

export interface RotationScoreRequest {
  location: Location;
  current_crops: string[];
  priorities: Priorities;
  season_config?: SeasonConfig;
  top_n?: number;
}

export interface StressTestRequest {
  location: Location;
  current_crops: string[];
  priorities: Priorities;
  scenario?: StressScenario;
  top_n?: number;
}

export interface FarmAnalyzeRequest {
  location: Location;
  current_crops: string[];
  priorities: Priorities;
  season_config?: SeasonConfig;
  include_stress_test?: boolean;
  top_n?: number;
}

export interface FarmAnalyzeResponse {
  location: Location;
  generated_at: string;
  climate: ClimateShiftResponse | null;
  soil: SoilProfileResponse | null;
  ndvi: NdviSummaryResponse | null;
  rotations: RotationsScoreResponse | null;
  stress_test: RotationsStressTestResponse | null;
  warnings: string[];
}

export interface ApiErrorBody {
  detail: string;
}

export const DEFAULT_PRIORITIES: Priorities = {
  save_water: 0.25,
  build_soil: 0.25,
  lower_climate_risk: 0.25,
  stay_close_to_current: 0.25,
  income_proxy: null,
};

// ---------------------------------------------------------------------------
// AI Agronomist advisor (/advisor/explain, /advisor/chat)
// ---------------------------------------------------------------------------

export type AdvisorLanguage = "en" | "ur";

/** "top_0" | "pareto_0" | ... -- index into FarmAnalyzeResponse.rotations.top
 * or .pareto_optimal, exactly as the backend resolves it. */
export type RotationId = string;

export interface AdvisorExplainRequest {
  analysis?: FarmAnalyzeResponse | null;
  rotation_id: RotationId;
  current_crops: string[];
  language: AdvisorLanguage;
}

export interface AdvisorExplainResponse {
  text: string;
  technical_note: string;
  language: AdvisorLanguage;
  verified: boolean;
  issues: string[];
  rewrites_used: number;
  facts_used: Record<string, unknown>;
  kb_sources: string[];
  model_used: string;
}

export interface AdvisorChatRequest {
  analysis?: FarmAnalyzeResponse | null;
  rotation_id?: RotationId;
  current_crops: string[];
  question: string;
  language: AdvisorLanguage;
}

export interface AdvisorChatResponse {
  answer: string;
  language: AdvisorLanguage;
  verified: boolean;
  issues: string[];
  answerable: boolean;
  rewrites_used: number;
  facts_used: Record<string, unknown>;
  kb_sources: string[];
  model_used: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  response?: AdvisorChatResponse;
}

// ---------------------------------------------------------------------------
// Soil presets (/soil/presets)
// ---------------------------------------------------------------------------

export type SoilTexture = "sand" | "sandy_loam" | "loam" | "silt_loam" | "clay_loam" | "clay";

export interface SoilPreset {
  texture: SoilTexture;
  phh2o: number;
  clay_pct: number;
  sand_pct: number;
  silt_pct: number;
  soc_g_kg: number;
  nitrogen_g_kg: number;
  cec_cmol_kg: number;
}

export interface SoilPresetsResponse {
  presets: SoilPreset[];
  source: SourceMeta;
}

// ---------------------------------------------------------------------------
// PDF report (/report/pdf)
// ---------------------------------------------------------------------------

export interface ReportPdfRequest {
  analysis?: FarmAnalyzeResponse | null;
  current_crops: string[];
  language: AdvisorLanguage;
  top_n?: number;
}
