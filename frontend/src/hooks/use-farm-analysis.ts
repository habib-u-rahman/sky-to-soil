"use client";

import { useEffect } from "react";
import { useFarmAnalysisStore } from "@/lib/farm-analysis-store";
import { useFarmStore } from "@/lib/farm-store";

/** Loads (and caches) the combined farm analysis for whatever location /
 * crops / priorities are currently in the farm store. Shared between the
 * dashboard and rotations pages so navigating between them doesn't re-fetch. */
export function useFarmAnalysis() {
  const location = useFarmStore((s) => s.location);
  const currentCrops = useFarmStore((s) => s.currentCrops);
  const priorities = useFarmStore((s) => s.priorities);
  const setupComplete = useFarmStore((s) => s.setupComplete);
  const isDemo = useFarmStore((s) => s.isDemo);

  const { data, status, error, load } = useFarmAnalysisStore();

  useEffect(() => {
    if (location) {
      void load(location, currentCrops, priorities, isDemo);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location?.lat, location?.lon, JSON.stringify(currentCrops), JSON.stringify(priorities), isDemo]);

  return {
    data,
    status,
    error,
    isDemo,
    hasFarm: setupComplete && !!location,
    retry: () => location && load(location, currentCrops, priorities, isDemo),
  };
}
