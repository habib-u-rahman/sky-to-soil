"use client";

import { cropVisual } from "@/lib/crop-meta";
import { useI18n } from "@/i18n";
import type { CropProfile, RotationPlan } from "@/types/api";

interface RotationTimelineProps {
  rotation: RotationPlan;
  crops: CropProfile[] | null;
}

function cropName(cropId: string | null, crops: CropProfile[] | null, fallowLabel: string): string {
  if (!cropId) return fallowLabel;
  return crops?.find((c) => c.id === cropId)?.name.split(" (")[0] ?? cropId;
}

export function RotationTimeline({ rotation, crops }: RotationTimelineProps) {
  const { t } = useI18n();
  const fallow = t("rotations.fallow");

  const years = [
    { label: t("rotations.yearLabel", { year: 1 }), slots: [rotation.Y1_kharif, rotation.Y1_rabi] as const },
    { label: t("rotations.yearLabel", { year: 2 }), slots: [rotation.Y2_kharif, rotation.Y2_rabi] as const },
  ];
  const seasonLabels = [t("rotations.kharifShort"), t("rotations.rabiShort")];

  return (
    <div className="space-y-2">
      {years.map((year) => (
        <div key={year.label}>
          <p className="mb-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">{year.label}</p>
          <div className="grid grid-cols-2 gap-1.5">
            {year.slots.map((cropId, i) => {
              const visual = cropVisual(cropId);
              return (
                <div
                  key={i}
                  className="flex flex-col items-center gap-1 rounded-md border border-border px-2 py-2 text-center"
                  style={{ backgroundColor: cropId ? `color-mix(in oklch, ${visual.color} 12%, var(--card))` : undefined }}
                >
                  <span className="text-base" aria-hidden>
                    {visual.icon}
                  </span>
                  <span className="line-clamp-1 text-[11px] font-medium text-foreground">
                    {cropName(cropId, crops, fallow)}
                  </span>
                  <span className="text-[9px] text-muted-foreground">{seasonLabels[i]}</span>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
