import { AlertTriangle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useI18n } from "@/i18n";
import type { SoilDepthLayer, SoilProfileResponse } from "@/types/api";

function DepthRow({ layer, t }: { layer: SoilDepthLayer; t: (path: string) => string }) {
  const depthLabels: Record<string, string> = {
    "0-5cm": t("setup.soilDepth05"),
    "5-15cm": t("setup.soilDepth515"),
    "15-30cm": t("setup.soilDepth1530"),
  };
  const fields: { key: keyof SoilDepthLayer; label: string }[] = [
    { key: "phh2o", label: t("setup.soilPh") },
    { key: "clay_pct", label: t("setup.soilClay") },
    { key: "sand_pct", label: t("setup.soilSand") },
    { key: "silt_pct", label: t("setup.soilSilt") },
    { key: "soc_g_kg", label: t("setup.soilSoc") },
    { key: "nitrogen_g_kg", label: t("setup.soilNitrogen") },
    { key: "cec_cmol_kg", label: t("setup.soilCec") },
  ];

  return (
    <div className="rounded-lg border border-border p-3">
      <p className="mb-2 text-xs font-semibold text-foreground">{depthLabels[layer.depth] ?? layer.depth}</p>
      <dl className="grid grid-cols-2 gap-1.5 text-xs">
        {fields.map((f) => (
          <div key={f.key} className="flex items-center justify-between gap-2">
            <dt className="text-muted-foreground">{f.label}</dt>
            <dd className="font-mono text-foreground">{(layer[f.key] as number | null) ?? "—"}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export function SoilProfileCard({ soil }: { soil: SoilProfileResponse }) {
  const { t } = useI18n();
  const isManual = soil.status === "manual_input_needed" || soil.status === "unavailable";

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{t("dashboard.soilProfileTitle")}</CardTitle>
          <Badge variant={isManual ? "outline" : "secondary"}>{soil.source.source}</Badge>
        </div>
        <CardDescription>{t("dashboard.soilProfileDesc")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {isManual && (
          <div className="flex items-start gap-2 rounded-lg border border-warning/30 bg-warning/10 px-3 py-2 text-xs">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warning" />
            <p>{t("dashboard.soilManualBanner")}</p>
          </div>
        )}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {soil.layers.map((layer) => (
            <DepthRow key={layer.depth} layer={layer} t={t} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
