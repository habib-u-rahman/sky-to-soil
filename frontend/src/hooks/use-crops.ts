"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import type { CropProfile } from "@/types/api";

let cache: CropProfile[] | null = null;
let inflight: Promise<CropProfile[]> | null = null;

async function fetchCrops(): Promise<CropProfile[]> {
  if (cache) return cache;
  if (!inflight) {
    inflight = api
      .crops()
      .then((res) => {
        cache = res.crops;
        return res.crops;
      })
      .catch((err) => {
        // api.crops() itself falls back to the bundled list on failure and
        // shouldn't reject -- but if it somehow still does, don't leave
        // this module permanently stuck returning a rejected promise for
        // the rest of the session; let the next caller retry.
        inflight = null;
        throw err;
      });
  }
  return inflight;
}

export function useCrops() {
  const [crops, setCrops] = useState<CropProfile[] | null>(cache);

  useEffect(() => {
    if (cache) return;
    fetchCrops()
      .then(setCrops)
      .catch(() => {
        // Nothing more to fall back to here -- crop names/icons just won't
        // render for this session; the rest of the UI already treats a
        // missing crop profile gracefully (falls back to the raw id).
      });
  }, []);

  return crops;
}
