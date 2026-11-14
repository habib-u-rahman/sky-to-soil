"use client";

import { TrendingDown, TrendingUp, Minus } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { useI18n } from "@/i18n";
import type { ClimateShiftResponse } from "@/types/api";

const THEN_COLOR = "var(--chart-3)";
const NOW_COLOR = "var(--chart-2)";

interface ClimateChartsProps {
  climate: ClimateShiftResponse;
}

export function TempWetnessChart({ climate }: ClimateChartsProps) {
  const { t } = useI18n();
  const { baseline, recent } = climate;

  const data = [
    {
      name: `${t("dashboard.kpiTempChange")} max (°C)`,
      then: baseline.mean_tmax_c ?? 0,
      now: recent.mean_tmax_c ?? 0,
    },
    {
      name: `${t("dashboard.kpiTempChange")} min (°C)`,
      then: baseline.mean_tmin_c ?? 0,
      now: recent.mean_tmin_c ?? 0,
    },
    {
      name: `${t("dashboard.kpiSoilWetness")} (×100)`,
      then: (baseline.mean_root_zone_wetness ?? 0) * 100,
      now: (recent.mean_root_zone_wetness ?? 0) * 100,
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("dashboard.chartMonthlyClimateTitle")}</CardTitle>
        <CardDescription>
          {t("dashboard.chartMonthlyClimateDesc", { baseline: baseline.period_label, recent: recent.period_label })}
        </CardDescription>
      </CardHeader>
      <CardContent className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} />
            <YAxis tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} />
            <Tooltip
              contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} formatter={(value) => (value === "then" ? t("dashboard.thenLabel") : t("dashboard.nowLabel"))} />
            <Bar dataKey="then" name="then" fill={THEN_COLOR} radius={[4, 4, 0, 0]} />
            <Bar dataKey="now" name="now" fill={NOW_COLOR} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

export function HotDaysChart({ climate }: ClimateChartsProps) {
  const { t } = useI18n();
  const { baseline, recent } = climate;

  const data = [
    {
      name: t("dashboard.kharifShort"),
      then: baseline.hot_days_gt35_by_season.kharif ?? 0,
      now: recent.hot_days_gt35_by_season.kharif ?? 0,
    },
    {
      name: t("dashboard.rabiShort"),
      then: baseline.hot_days_gt35_by_season.rabi ?? 0,
      now: recent.hot_days_gt35_by_season.rabi ?? 0,
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("dashboard.chartHotDaysTrendTitle")}</CardTitle>
        <CardDescription>
          {t("dashboard.chartHotDaysTrendDesc", { baseline: baseline.period_label, recent: recent.period_label })}
        </CardDescription>
      </CardHeader>
      <CardContent className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 12, fill: "var(--muted-foreground)" }} />
            <YAxis tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} />
            <Tooltip
              contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} formatter={(value) => (value === "then" ? t("dashboard.thenLabel") : t("dashboard.nowLabel"))} />
            <Bar dataKey="then" name="then" fill={THEN_COLOR} radius={[4, 4, 0, 0]} />
            <Bar dataKey="now" name="now" fill="var(--warning)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

export function RainfallChart({ climate }: ClimateChartsProps) {
  const { t } = useI18n();
  const { baseline, recent } = climate;

  const data = [
    {
      name: t("dashboard.kharifShort"),
      then: baseline.seasonal_rainfall_mm.kharif_mm ?? 0,
      now: recent.seasonal_rainfall_mm.kharif_mm ?? 0,
    },
    {
      name: t("dashboard.rabiShort"),
      then: baseline.seasonal_rainfall_mm.rabi_mm ?? 0,
      now: recent.seasonal_rainfall_mm.rabi_mm ?? 0,
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("dashboard.chartRainfallTitle")}</CardTitle>
        <CardDescription>{t("dashboard.chartRainfallDesc")}</CardDescription>
      </CardHeader>
      <CardContent className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 12, fill: "var(--muted-foreground)" }} />
            <YAxis tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} unit="mm" />
            <Tooltip
              contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} formatter={(value) => (value === "then" ? t("dashboard.thenLabel") : t("dashboard.nowLabel"))} />
            <Bar dataKey="then" name="then" fill={THEN_COLOR} radius={[4, 4, 0, 0]} />
            <Bar dataKey="now" name="now" fill="var(--sky)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

export function TrendSignals({ climate }: ClimateChartsProps) {
  const { t } = useI18n();

  const labels: Record<string, string> = {
    annual_mean_tmax_c: `${t("dashboard.kpiTempChange")} (max)`,
    annual_mean_tmin_c: `${t("dashboard.kpiTempChange")} (min)`,
    root_zone_wetness: t("dashboard.kpiSoilWetness"),
    kharif_rainfall_mm: `${t("dashboard.kharifShort")} ${t("dashboard.kpiRainfall")}`,
    rabi_rainfall_mm: `${t("dashboard.rabiShort")} ${t("dashboard.kpiRainfall")}`,
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("dashboard.trendSignalsTitle")}</CardTitle>
        <CardDescription>
          {t("dashboard.trendSignalsDesc", { start: climate.baseline.start_year, end: climate.recent.end_year })}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2.5">
        {climate.trends.map((trend) => {
          const Icon = trend.mk_trend === "increasing" ? TrendingUp : trend.mk_trend === "decreasing" ? TrendingDown : Minus;
          const tone =
            trend.mk_trend === "increasing" ? "text-warning" : trend.mk_trend === "decreasing" ? "text-sky" : "text-muted-foreground";
          return (
            <div key={trend.variable} className="flex items-center justify-between gap-3 rounded-md border border-border px-3 py-2">
              <div className="flex items-center gap-2">
                <Icon className={`h-4 w-4 ${tone}`} aria-hidden />
                <span className="text-sm text-foreground">{labels[trend.variable] ?? trend.variable}</span>
              </div>
              <div className="flex items-center gap-2" title={trend.significant_at_0_10 ? t("dashboard.trendSignificant") : t("dashboard.trendNotSignificant")}>
                {trend.sen_slope_per_year !== null && (
                  <span className="text-xs font-mono text-muted-foreground">
                    {trend.sen_slope_per_year >= 0 ? "+" : ""}
                    {trend.sen_slope_per_year.toFixed(3)} {t("dashboard.perYear")}
                  </span>
                )}
                <Badge variant={trend.significant_at_0_10 ? "default" : "secondary"} className="text-[10px]">
                  {trend.mk_trend === "increasing"
                    ? t("dashboard.trendIncreasing")
                    : trend.mk_trend === "decreasing"
                      ? t("dashboard.trendDecreasing")
                      : t("dashboard.trendNone")}
                </Badge>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
