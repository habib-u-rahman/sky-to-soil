"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import type { CropProfile } from "@/types/api";

let cache: CropProfile[] | null = null;
let inflight: Promise<CropProfile[]> | null = null;

async function fetchCrops(): Promise<CropProfile[]> {
  if (cache) return cache;
  if (!inflight) {
    inflight = api.crops().then((res) => {
      cache = res.crops;
      return res.crops;
    });
  }
  return inflight;
}

export function useCrops() {
  const [crops, setCrops] = useState<CropProfile[] | null>(cache);

  useEffect(() => {
    if (cache) return;
    fetchCrops().then(setCrops);
  }, []);

  return crops;
}
