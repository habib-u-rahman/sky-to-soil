import { API_URL, USE_MOCK } from "@/lib/config";
import {
  mockClimate,
  mockCrops,
  mockFarmAnalyze,
  mockHealth,
  mockNdvi,
  mockRotationsScore,
  mockSoil,
  mockStressTest,
} from "@/mocks";
import type {
  ClimateShiftResponse,
  CropsListResponse,
  FarmAnalyzeRequest,
  FarmAnalyzeResponse,
  HealthResponse,
  Location,
  NdviSummaryResponse,
  RotationScoreRequest,
  RotationsScoreResponse,
  RotationsStressTestResponse,
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

async function get<T>(path: string, params: Record<string, string | number | boolean | undefined>): Promise<T> {
  const url = new URL(path, API_URL);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined) url.searchParams.set(key, String(value));
  });
  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(body.detail ?? `Request failed (${res.status})`, res.status);
  }
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const url = new URL(path, API_URL);
  const res = await fetch(url.toString(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(errBody.detail ?? `Request failed (${res.status})`, res.status);
  }
  return res.json();
}

/** Small artificial delay so mock mode still shows loading states. */
async function mockDelay<T>(value: T, ms = 450): Promise<T> {
  await new Promise((resolve) => setTimeout(resolve, ms));
  return value;
}

export const api = {
  async health(): Promise<HealthResponse> {
    if (USE_MOCK) return mockDelay(mockHealth);
    return get("/health", {});
  },

  async climate(location: Location): Promise<ClimateShiftResponse> {
    if (USE_MOCK) return mockDelay(mockClimate);
    return get("/climate", { lat: location.lat, lon: location.lon });
  },

  async soil(location: Location): Promise<SoilProfileResponse> {
    if (USE_MOCK) return mockDelay(mockSoil);
    return get("/soil", { lat: location.lat, lon: location.lon });
  },

  async ndvi(location: Location): Promise<NdviSummaryResponse> {
    if (USE_MOCK) return mockDelay(mockNdvi);
    return get("/ndvi", { lat: location.lat, lon: location.lon });
  },

  async crops(): Promise<CropsListResponse> {
    if (USE_MOCK) return mockDelay(mockCrops);
    return get("/crops", {});
  },

  async scoreRotations(body: RotationScoreRequest): Promise<RotationsScoreResponse> {
    if (USE_MOCK) return mockDelay(mockRotationsScore);
    return post("/rotations/score", body);
  },

  async stressTest(body: StressTestRequest): Promise<RotationsStressTestResponse> {
    if (USE_MOCK) return mockDelay(mockStressTest);
    return post("/rotations/stress-test", body);
  },

  async analyzeFarm(body: FarmAnalyzeRequest): Promise<FarmAnalyzeResponse> {
    if (USE_MOCK) return mockDelay(mockFarmAnalyze, 700);
    return post("/farm/analyze", body);
  },
};
