import { KpiCard, type KpiTone, type KpiTrend } from "@/components/dashboard/kpi-card";
import type { ClimateShiftResponse } from "@/types/api";

function trendOf(delta: number, epsilon = 0.05): KpiTrend {
  if (delta > epsilon) return "up";
  if (delta < -epsilon) return "down";
  return "flat";
}

interface ClimateKpiGridProps {
  climate: ClimateShiftResponse;
  t: (path: string, vars?: Record<string, string | number>) => string;
}

export function ClimateKpiGrid({ climate, t }: ClimateKpiGridProps) {
  const { baseline, recent, deltas } = climate;

  const tempDelta = deltas.mean_tmax_c ?? 0;
  const hotDaysBaseline = (baseline.hot_days_gt35_by_season.kharif ?? 0) + (baseline.hot_days_gt35_by_season.rabi ?? 0);
  const hotDaysRecent = (recent.hot_days_gt35_by_season.kharif ?? 0) + (recent.hot_days_gt35_by_season.rabi ?? 0);
  const hotDaysDelta = hotDaysRecent - hotDaysBaseline;
  const rainBaseline = (baseline.seasonal_rainfall_mm.kharif_mm ?? 0) + (baseline.seasonal_rainfall_mm.rabi_mm ?? 0);
  const rainRecent = (recent.seasonal_rainfall_mm.kharif_mm ?? 0) + (recent.seasonal_rainfall_mm.rabi_mm ?? 0);
  const rainDelta = rainRecent - rainBaseline;
  const wetnessDelta = (deltas.mean_root_zone_wetness ?? 0) * 100;

  function toneFor(delta: number, warmIsWarning: boolean): KpiTone {
    const trend = trendOf(delta);
    if (trend === "flat") return "neutral";
    const isIncrease = trend === "up";
    return isIncrease === warmIsWarning ? "warning" : "success";
  }

  const sinceLabel = t("dashboard.since", { baseline: baseline.period_label, recent: recent.period_label });

  const cards: Array<{ key: string; title: string; value: string; trend: KpiTrend; tone: KpiTone; description: string }> = [
    {
      key: "temp",
      title: t("dashboard.kpiTempChange"),
      value: `${tempDelta >= 0 ? "+" : ""}${tempDelta.toFixed(1)}°C`,
      trend: trendOf(tempDelta),
      tone: toneFor(tempDelta, true),
      description: `${Math.abs(tempDelta).toFixed(1)}°C ${tempDelta >= 0 ? t("dashboard.warmer") : t("dashboard.cooler")} · ${sinceLabel}`,
    },
    {
      key: "hotdays",
      title: t("dashboard.kpiHotDays"),
      value: `${hotDaysDelta >= 0 ? "+" : ""}${hotDaysDelta.toFixed(0)}`,
      trend: trendOf(hotDaysDelta, 0.5),
      tone: toneFor(hotDaysDelta, true),
      description: `${Math.abs(hotDaysDelta).toFixed(0)} ${hotDaysDelta >= 0 ? t("dashboard.moreDays") : t("dashboard.fewerDays")}`,
    },
    {
      key: "rainfall",
      title: t("dashboard.kpiRainfall"),
      value: `${rainDelta >= 0 ? "+" : ""}${rainDelta.toFixed(0)} mm`,
      trend: trendOf(rainDelta, 2),
      tone: toneFor(rainDelta, false),
      description: `${Math.abs(rainDelta).toFixed(0)} mm ${rainDelta >= 0 ? t("dashboard.wetter") : t("dashboard.drier")} · ${sinceLabel}`,
    },
    {
      key: "wetness",
      title: t("dashboard.kpiSoilWetness"),
      value: `${wetnessDelta >= 0 ? "+" : ""}${wetnessDelta.toFixed(1)} pp`,
      trend: trendOf(wetnessDelta, 0.5),
      tone: toneFor(wetnessDelta, false),
      description: `${wetnessDelta >= 0 ? t("dashboard.wetter") : t("dashboard.drier")} · ${sinceLabel}`,
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <KpiCard key={card.key} title={card.title} value={card.value} trend={card.trend} tone={card.tone} description={card.description} />
      ))}
    </div>
  );
}
