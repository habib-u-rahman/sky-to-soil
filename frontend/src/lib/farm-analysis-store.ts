"use client";

import { create } from "zustand";
import { api, ApiError } from "@/lib/api-client";
import { allCurrentCrops } from "@/lib/farm-store";
import type { CurrentCrops } from "@/lib/farm-store";
import type { FarmAnalyzeResponse, Location, Priorities } from "@/types/api";

interface FarmAnalysisState {
  signature: string | null;
  data: FarmAnalyzeResponse | null;
  status: "idle" | "loading" | "ready" | "error";
  error: string | null;
  load: (location: Location, currentCrops: CurrentCrops, priorities: Priorities, demo: boolean) => Promise<void>;
}

function buildSignature(location: Location, currentCrops: CurrentCrops, priorities: Priorities, demo: boolean): string {
  return JSON.stringify({ location, currentCrops, priorities, demo });
}

export const useFarmAnalysisStore = create<FarmAnalysisState>((set, get) => ({
  signature: null,
  data: null,
  status: "idle",
  error: null,
  async load(location, currentCrops, priorities, demo) {
    const signature = buildSignature(location, currentCrops, priorities, demo);
    if (get().signature === signature && (get().status === "ready" || get().status === "loading")) return;

    set({ status: "loading", error: null, signature });
    try {
      // demo=true hits the backend's frozen Faisalabad dataset instantly --
      // no live NASA POWER / MODIS / SoilGrids calls -- so the "Try demo
      // farm" button always works even if those upstreams are slow/down.
      const data = await api.analyzeFarm(
        {
          location,
          current_crops: allCurrentCrops(currentCrops),
          priorities,
          include_stress_test: true,
          top_n: 10,
        },
        demo
      );
      if (get().signature !== signature) return; // a newer request superseded this one
      set({ data, status: "ready" });
    } catch (err) {
      if (get().signature !== signature) return;
      set({ status: "error", error: err instanceof ApiError ? err.message : "Failed to load farm analysis" });
    }
  },
}));
