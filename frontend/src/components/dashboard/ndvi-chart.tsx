"use client";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useI18n } from "@/i18n";
import type { NdviSummaryResponse } from "@/types/api";

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
              <YAxis domain={[-0.2, 1]} tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} />
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
