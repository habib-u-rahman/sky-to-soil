"use client";

import { useEffect, useState } from "react";
import { ErrorState } from "@/components/shared/error-state";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useI18n } from "@/i18n";
import { api, ApiError } from "@/lib/api-client";
import { cropVisual } from "@/lib/crop-meta";
import type { CurrentCrops } from "@/lib/farm-store";
import type { CropProfile } from "@/types/api";
import { cn } from "@/lib/utils";

interface StepCropsProps {
  value: CurrentCrops;
  onChange: (value: CurrentCrops) => void;
}

export function StepCrops({ value, onChange }: StepCropsProps) {
  const { t } = useI18n();
  const [crops, setCrops] = useState<CropProfile[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .crops()
      .then((res) => setCrops(res.crops))
      .catch((err) => setError(err instanceof ApiError ? err.message : t("states.errorDesc")));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function toggle(season: "kharif" | "rabi", cropId: string) {
    const current = value[season];
    const next = current.includes(cropId) ? current.filter((id) => id !== cropId) : [...current, cropId];
    onChange({ ...value, [season]: next });
  }

  function renderGroup(season: "kharif" | "rabi", label: string) {
    const seasonCrops = crops?.filter((c) => c.season === season || c.season === "either") ?? [];
    return (
      <div>
        <h3 className="mb-3 text-sm font-semibold text-foreground">{label}</h3>
        <div className="flex flex-wrap gap-2">
          {seasonCrops.map((crop) => {
            const selected = value[season].includes(crop.id);
            const visual = cropVisual(crop.id);
            return (
              <Button
                key={crop.id}
                type="button"
                variant={selected ? "default" : "outline"}
                size="sm"
                onClick={() => toggle(season, crop.id)}
                className={cn("gap-1.5", selected && "ring-2 ring-primary/30")}
              >
                <span aria-hidden>{visual.icon}</span>
                {crop.name}
              </Button>
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-foreground">{t("setup.cropsTitle")}</h2>
        <p className="mt-1 text-sm text-muted-foreground">{t("setup.cropsDesc")}</p>
      </div>

      {error && <ErrorState description={error} />}

      {!crops && !error ? (
        <div className="space-y-6">
          {[0, 1].map((i) => (
            <div key={i} className="space-y-3">
              <Skeleton className="h-4 w-32" />
              <div className="flex flex-wrap gap-2">
                {Array.from({ length: 6 }).map((_, j) => (
                  <Skeleton key={j} className="h-8 w-24 rounded-md" />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-6">
          {renderGroup("kharif", t("setup.cropsKharifLabel"))}
          {renderGroup("rabi", t("setup.cropsRabiLabel"))}
        </div>
      )}
    </div>
  );
}
