"use client";

import { PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer } from "recharts";
import { useI18n } from "@/i18n";
import type { RotationSubScores } from "@/types/api";

export function SubScoreRadar({ subScores }: { subScores: RotationSubScores }) {
  const { t } = useI18n();

  const data = [
    { metric: t("rotations.waterFit"), value: subScores.water_fit },
    { metric: t("rotations.heatRisk"), value: subScores.heat_risk },
    { metric: t("rotations.soilHealth"), value: subScores.soil_health },
    { metric: t("rotations.soilSuitability"), value: subScores.soil_suitability },
  ];

  return (
    <div className="h-40">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} margin={{ top: 4, bottom: 4 }}>
          <PolarGrid stroke="var(--border)" />
          <PolarAngleAxis dataKey="metric" tick={{ fontSize: 9, fill: "var(--muted-foreground)" }} />
          <Radar dataKey="value" stroke="var(--crop)" fill="var(--crop)" fillOpacity={0.35} isAnimationActive={false} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SubScoreBars({ subScores }: { subScores: RotationSubScores }) {
  const { t } = useI18n();
  const items: { label: string; value: number }[] = [
    { label: t("rotations.waterFit"), value: subScores.water_fit },
    { label: t("rotations.heatRisk"), value: subScores.heat_risk },
    { label: t("rotations.soilHealth"), value: subScores.soil_health },
    { label: t("rotations.soilSuitability"), value: subScores.soil_suitability },
  ];

  return (
    <div className="space-y-1.5">
      {items.map((item) => (
        <div key={item.label} className="flex items-center gap-2">
          <span className="w-24 shrink-0 text-[11px] text-muted-foreground">{item.label}</span>
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
            <div className="h-full rounded-full bg-crop" style={{ width: `${Math.max(item.value, 2)}%` }} />
          </div>
          <span className="w-8 shrink-0 text-end text-[11px] font-mono text-muted-foreground">{Math.round(item.value)}</span>
        </div>
      ))}
    </div>
  );
}
