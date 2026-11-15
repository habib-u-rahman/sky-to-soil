import { API_URL, USE_MOCK } from "@/lib/config";
import {
  mockAdvisorChatByQuestion,
  mockAdvisorExplainTop0,
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

/** Render's free tier sleeps after inactivity; a cold start can take up to
 * ~60s. For `demo=true` requests specifically we already have the exact
 * right answer bundled in the frontend build (see @/mocks), so there's no
 * reason to make a judge wait through a cold start just to see the demo
 * farm -- race the live call against a short timeout and fall back to the
 * bundled copy the instant either one fails or the timeout fires. Never
 * used for live (non-demo) requests: those have no bundled answer to fall
 * back to, and the caller is expected to show the "waking up" progress
 * screen instead (see use-farm-analysis.ts). */
const DEMO_FALLBACK_TIMEOUT_MS = 4000;

function withDemoFallback<T>(demo: boolean, attempt: () => Promise<T>, fallback?: () => T): Promise<T> {
  if (!demo || !fallback) return attempt();

  return new Promise<T>((resolve) => {
    let settled = false;
    const timer = setTimeout(() => {
      if (!settled) {
        settled = true;
        resolve(fallback());
      }
    }, DEMO_FALLBACK_TIMEOUT_MS);

    attempt()
      .then((value) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        resolve(value);
      })
      .catch(() => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        resolve(fallback());
      });
  });
}

/** Fire-and-forget ping to wake a sleeping Render free-tier instance
 * before the farmer actually needs it. Safe to call from a client
 * component on mount -- failures are expected (and silently swallowed)
 * when the backend is genuinely down, since this is a best-effort nudge,
 * not something the caller should wait on. */
export function wakeBackend(): void {
  if (USE_MOCK) return;
  void fetch(buildUrl("/health").toString(), { cache: "no-store" }).catch(() => {});
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

  /** Same reasoning as crops() above: the 6 texture presets are static. */
  async soilPresets(): Promise<SoilPresetsResponse> {
    if (USE_MOCK) return mockDelay(mockSoilPresets);
    try {
      return await get("/soil/presets");
    } catch {
      return mockSoilPresets;
    }
  },

  async ndvi(location: Location): Promise<NdviSummaryResponse> {
    if (USE_MOCK) return mockDelay(mockNdvi);
    return get("/ndvi", { lat: location.lat, lon: location.lon });
  },

  /** The 14-crop knowledge base is static -- identical whether the backend
   * is reachable or not -- so unlike farm-specific data this always falls
   * back to the bundled copy on any failure, not just when demo=true.
   * Without this, a single failed request here would otherwise leave crop
   * names/icons broken for the rest of the session (see useCrops' cache). */
  async crops(): Promise<CropsListResponse> {
    if (USE_MOCK) return mockDelay(mockCrops);
    try {
      return await get("/crops");
    } catch {
      return mockCrops;
    }
  },

  async scoreRotations(body: RotationScoreRequest, demo = false): Promise<RotationsScoreResponse> {
    if (USE_MOCK) return mockDelay(mockRotationsScore);
    return withDemoFallback(demo, () => post("/rotations/score", body, { demo }), demo ? () => mockRotationsScore : undefined);
  },

  async stressTest(body: StressTestRequest, demo = false): Promise<RotationsStressTestResponse> {
    if (USE_MOCK) return mockDelay(mockStressTest);
    return withDemoFallback(demo, () => post("/rotations/stress-test", body, { demo }), demo ? () => mockStressTest : undefined);
  },

  /** `demo: true` hits the backend's frozen Faisalabad dataset instantly,
   * skipping live NASA POWER / MODIS / SoilGrids calls entirely. On top of
   * that, withDemoFallback below means "Try demo farm" stays instant even
   * if the Render instance itself is asleep or unreachable. */
  async analyzeFarm(body: FarmAnalyzeRequest, demo = false): Promise<FarmAnalyzeResponse> {
    if (USE_MOCK) return mockDelay(mockFarmAnalyze, 700);
    return withDemoFallback(demo, () => post("/farm/analyze", body, { demo }), demo ? () => mockFarmAnalyze : undefined);
  },

  /** Groq-backed; expect a few seconds even when not using demo=true. In
   * demo mode, only rotation_id "top_0" has a bundled offline answer --
   * any other rotation genuinely needs the backend to be reachable. */
  async advisorExplain(body: AdvisorExplainRequest, demo = false): Promise<AdvisorExplainResponse> {
    const bundled = demo && body.rotation_id === "top_0" ? mockAdvisorExplainTop0[body.language] : undefined;
    return withDemoFallback(demo, () => post("/advisor/explain", body, { demo }), bundled ? () => bundled : undefined);
  },

  /** Same idea as advisorExplain: in demo mode, only the handful of sample
   * questions precomputed into the bundle (see app/scripts/build_demo.py)
   * have an offline answer. Anything else needs the backend reachable. */
  async advisorChat(body: AdvisorChatRequest, demo = false): Promise<AdvisorChatResponse> {
    const bundled = demo ? mockAdvisorChatByQuestion[body.language]?.find((q) => q.question === body.question)?.response : undefined;
    return withDemoFallback(demo, () => post("/advisor/chat", body, { demo }), bundled ? () => bundled : undefined);
  },

  /** Always English: the backend generates the advisor narrative for the
   * PDF in English regardless of the requested language. */
  async reportPdf(body: ReportPdfRequest, demo = false): Promise<Blob> {
    return postBlob("/report/pdf", body, { demo });
  },
};
