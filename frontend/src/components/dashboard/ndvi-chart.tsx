"use client";

import { Area, AreaChart, CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useI18n } from "@/i18n";
import type { NdviSummaryResponse } from "@/types/api";

const YEAR_COLORS = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)"];

const MONTH_START_DOY = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335];
function doyToMonthLabel(doy: number): string {
  const names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  let i = 0;
  while (i < 11 && doy >= MONTH_START_DOY[i + 1]) i++;
  return names[i];
}

/** Pivots points into one row per MODIS composite day-of-year, one column
 * per calendar year -- lets every year's seasonal curve overlay on a shared
 * x-axis so the two cropping-season peaks line up across years. */
export function NdviYearOverYearChart({ ndvi }: { ndvi: NdviSummaryResponse }) {
  const { t } = useI18n();

  const years = Array.from(
    new Set(ndvi.points.map((p) => Number.parseInt(p.modis_date.slice(1, 5), 10)))
  ).sort((a, b) => a - b);

  const rowsByDoy = new Map<number, Record<string, number | null>>();
  for (const p of ndvi.points) {
    if (!p.usable || p.ndvi === null) continue;
    const year = Number.parseInt(p.modis_date.slice(1, 5), 10);
    const doy = Number.parseInt(p.modis_date.slice(5, 8), 10);
    if (!rowsByDoy.has(doy)) rowsByDoy.set(doy, { doy });
    rowsByDoy.get(doy)![String(year)] = p.ndvi;
  }
  const data = Array.from(rowsByDoy.values()).sort((a, b) => (a.doy as number) - (b.doy as number));

  if (years.length < 2 || data.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("dashboard.chartNdviYoyTitle")}</CardTitle>
        <CardDescription>{t("dashboard.chartNdviYoyDesc")}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis
                dataKey="doy"
                tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
                tickFormatter={(doy: number) => doyToMonthLabel(doy)}
                ticks={MONTH_START_DOY}
                type="number"
                domain={[1, 366]}
              />
              <YAxis
                domain={[-0.2, 1]}
                tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                label={{ value: "NDVI (0-1)", angle: -90, position: "insideLeft", fontSize: 11, fill: "var(--muted-foreground)" }}
              />
              <Tooltip
                contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
                labelFormatter={(doy) => doyToMonthLabel(Number(doy))}
                formatter={(value) => (typeof value === "number" ? value.toFixed(3) : "—")}
              />
              <ReferenceLine y={0.5} stroke="var(--warning)" strokeDasharray="4 4" label={{ value: t("dashboard.ndviYoyThresholdLabel"), fontSize: 10, fill: "var(--warning)", position: "insideTopLeft" }} />
              {years.map((year, i) => (
                <Line
                  key={year}
                  type="monotone"
                  dataKey={String(year)}
                  name={String(year)}
                  stroke={YEAR_COLORS[i % YEAR_COLORS.length]}
                  strokeWidth={2}
                  dot={false}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          {years.map((year, i) => (
            <Badge key={year} variant="outline" style={{ borderColor: YEAR_COLORS[i % YEAR_COLORS.length], color: YEAR_COLORS[i % YEAR_COLORS.length] }}>
              {year}
            </Badge>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export function NdviChart({ ndvi }: { ndvi: NdviSummaryResponse }) {
  const { t } = useI18n();

  const data = ndvi.points.map((p) => ({
    date: p.calendar_date,
    ndvi: p.ndvi,
    usable: p.usable,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("dashboard.chartNdviTitle")}</CardTitle>
        <CardDescription>{t("dashboard.chartNdviDesc")}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="mb-3 flex flex-wrap items-center gap-3">
          {ndvi.mean_ndvi_good_quality !== null && (
            <Badge variant="secondary">
              {t("dashboard.ndviMeanLabel")}: {ndvi.mean_ndvi_good_quality.toFixed(3)}
            </Badge>
          )}
          {ndvi.pct_usable !== null && (
            <Badge variant="outline">
              {t("dashboard.ndviUsableLabel")}: {ndvi.pct_usable.toFixed(0)}%
            </Badge>
          )}
        </div>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
              <defs>
                <linearGradient id="ndviFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--crop)" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="var(--crop)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
                tickFormatter={(value: string) => value.slice(5)}
                minTickGap={24}
              />
              <YAxis
                domain={[-0.2, 1]}
                tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                label={{ value: "NDVI (0-1)", angle: -90, position: "insideLeft", fontSize: 11, fill: "var(--muted-foreground)" }}
              />
              <Tooltip
                contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
                formatter={(value) => (typeof value === "number" ? value.toFixed(4) : "—")}
              />
              <Area
                type="monotone"
                dataKey="ndvi"
                stroke="var(--crop)"
                strokeWidth={2}
                fill="url(#ndviFill)"
                connectNulls
                dot={{ r: 2 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
