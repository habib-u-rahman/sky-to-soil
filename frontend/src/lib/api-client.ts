import { API_URL, USE_MOCK } from "@/lib/config";
import {
  mockClimate,
  mockCrops,
  mockFarmAnalyze,
  mockHealth,
  mockNdvi,
  mockRotationsScore,
  mockSoil,
  mockSoilPresets,
  mockStressTest,
} from "@/mocks";
import type {
  AdvisorChatRequest,
  AdvisorChatResponse,
  AdvisorExplainRequest,
  AdvisorExplainResponse,
  ClimateShiftResponse,
  CropsListResponse,
  FarmAnalyzeRequest,
  FarmAnalyzeResponse,
  HealthResponse,
  Location,
  NdviSummaryResponse,
  ReportPdfRequest,
  RotationScoreRequest,
  RotationsScoreResponse,
  RotationsStressTestResponse,
  SoilPresetsResponse,
  SoilProfileResponse,
  StressTestRequest,
} from "@/types/api";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

function buildUrl(path: string, params: Record<string, string | number | boolean | undefined> = {}): URL {
  const url = new URL(path, API_URL);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined) url.searchParams.set(key, String(value));
  });
  return url;
}

async function parseErrorBody(res: Response): Promise<string> {
  const body = await res.json().catch(() => ({ detail: res.statusText }));
  return body.detail ?? `Request failed (${res.status})`;
}

async function get<T>(path: string, params: Record<string, string | number | boolean | undefined> = {}): Promise<T> {
  const res = await fetch(buildUrl(path, params).toString(), { cache: "no-store" });
  if (!res.ok) throw new ApiError(await parseErrorBody(res), res.status);
  return res.json();
}

async function post<T>(
  path: string,
  body: unknown,
  params: Record<string, string | number | boolean | undefined> = {}
): Promise<T> {
  const res = await fetch(buildUrl(path, params).toString(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) throw new ApiError(await parseErrorBody(res), res.status);
  return res.json();
}

/** POST that returns a binary body (PDF), not JSON. */
async function postBlob(
  path: string,
  body: unknown,
  params: Record<string, string | number | boolean | undefined> = {}
): Promise<Blob> {
  const res = await fetch(buildUrl(path, params).toString(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) throw new ApiError(await parseErrorBody(res), res.status);
  return res.blob();
}

/** Small artificial delay so mock mode still shows loading states. */
async function mockDelay<T>(value: T, ms = 450): Promise<T> {
  await new Promise((resolve) => setTimeout(resolve, ms));
  return value;
}

export const api = {
  async health(): Promise<HealthResponse> {
    if (USE_MOCK) return mockDelay(mockHealth);
    return get("/health");
  },

  async climate(location: Location): Promise<ClimateShiftResponse> {
    if (USE_MOCK) return mockDelay(mockClimate);
    return get("/climate", { lat: location.lat, lon: location.lon });
  },

  async soil(location: Location): Promise<SoilProfileResponse> {
    if (USE_MOCK) return mockDelay(mockSoil);
    return get("/soil", { lat: location.lat, lon: location.lon });
  },

  async soilPresets(): Promise<SoilPresetsResponse> {
    if (USE_MOCK) return mockDelay(mockSoilPresets);
    return get("/soil/presets");
  },

  async ndvi(location: Location): Promise<NdviSummaryResponse> {
    if (USE_MOCK) return mockDelay(mockNdvi);
    return get("/ndvi", { lat: location.lat, lon: location.lon });
  },

  async crops(): Promise<CropsListResponse> {
    if (USE_MOCK) return mockDelay(mockCrops);
    return get("/crops");
  },

  async scoreRotations(body: RotationScoreRequest, demo = false): Promise<RotationsScoreResponse> {
    if (USE_MOCK) return mockDelay(mockRotationsScore);
    return post("/rotations/score", body, { demo });
  },

  async stressTest(body: StressTestRequest, demo = false): Promise<RotationsStressTestResponse> {
    if (USE_MOCK) return mockDelay(mockStressTest);
    return post("/rotations/stress-test", body, { demo });
  },

  /** `demo: true` hits the backend's frozen Faisalabad dataset instantly,
   * skipping live NASA POWER / MODIS / SoilGrids calls entirely -- this is
   * what makes "Try demo farm" instant regardless of live-API health. */
  async analyzeFarm(body: FarmAnalyzeRequest, demo = false): Promise<FarmAnalyzeResponse> {
    if (USE_MOCK) return mockDelay(mockFarmAnalyze, 700);
    return post("/farm/analyze", body, { demo });
  },

  /** Groq-backed; expect a few seconds even when not using demo=true. */
  async advisorExplain(body: AdvisorExplainRequest, demo = false): Promise<AdvisorExplainResponse> {
    return post("/advisor/explain", body, { demo });
  },

  async advisorChat(body: AdvisorChatRequest, demo = false): Promise<AdvisorChatResponse> {
    return post("/advisor/chat", body, { demo });
  },

  /** Always English: the backend generates the advisor narrative for the
   * PDF in English regardless of the requested language. */
  async reportPdf(body: ReportPdfRequest, demo = false): Promise<Blob> {
    return postBlob("/report/pdf", body, { demo });
  },
};
