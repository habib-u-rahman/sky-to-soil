"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { DEMO_LOCATION } from "@/lib/config";
import { DEFAULT_PRIORITIES } from "@/types/api";
import type { Location, Priorities, SoilDepthLayer } from "@/types/api";

export interface CurrentCrops {
  kharif: string[];
  rabi: string[];
}

interface FarmState {
  location: Location | null;
  locationLabel: string | null;
  soilOverride: SoilDepthLayer[] | null;
  currentCrops: CurrentCrops;
  priorities: Priorities;
  isDemo: boolean;
  setupComplete: boolean;
  setLocation: (location: Location, label?: string) => void;
  setSoilOverride: (layers: SoilDepthLayer[] | null) => void;
  setCurrentCrops: (crops: CurrentCrops) => void;
  setPriorities: (priorities: Priorities) => void;
  completeSetup: () => void;
  loadDemoFarm: () => void;
  reset: () => void;
}

const emptyCrops: CurrentCrops = { kharif: [], rabi: [] };

export const useFarmStore = create<FarmState>()(
  persist(
    (set) => ({
      location: null,
      locationLabel: null,
      soilOverride: null,
      currentCrops: emptyCrops,
      priorities: DEFAULT_PRIORITIES,
      isDemo: false,
      setupComplete: false,
      setLocation: (location, label) => set({ location, locationLabel: label ?? null, isDemo: false }),
      setSoilOverride: (layers) => set({ soilOverride: layers }),
      setCurrentCrops: (crops) => set({ currentCrops: crops }),
      setPriorities: (priorities) => set({ priorities }),
      completeSetup: () => set({ setupComplete: true }),
      loadDemoFarm: () =>
        set({
          location: DEMO_LOCATION,
          locationLabel: "Faisalabad, Pakistan",
          currentCrops: { kharif: ["cotton"], rabi: ["wheat"] },
          priorities: { save_water: 0.3, build_soil: 0.3, lower_climate_risk: 0.2, stay_close_to_current: 0.2, income_proxy: null },
          isDemo: true,
          setupComplete: true,
        }),
      reset: () =>
        set({
          location: null,
          locationLabel: null,
          soilOverride: null,
          currentCrops: emptyCrops,
          priorities: DEFAULT_PRIORITIES,
          isDemo: false,
          setupComplete: false,
        }),
    }),
    { name: "sky-to-soil:farm" }
  )
);

export function allCurrentCrops(crops: CurrentCrops): string[] {
  return [...crops.kharif, ...crops.rabi];
}
