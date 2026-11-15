"use client";

import { Pencil, Check, AlertTriangle, Sprout } from "lucide-react";
import { useEffect, useState } from "react";
import { ErrorState } from "@/components/shared/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useI18n } from "@/i18n";
import { api, ApiError } from "@/lib/api-client";
import type { Location, SoilDepthLayer, SoilPreset, SoilTexture } from "@/types/api";

interface StepSoilProps {
  location: Location;
  override: SoilDepthLayer[] | null;
  onChange: (layers: SoilDepthLayer[] | null) => void;
}

const EMPTY_LAYERS: SoilDepthLayer[] = [
  { depth: "0-5cm", phh2o: null, clay_pct: null, sand_pct: null, silt_pct: null, soc_g_kg: null, nitrogen_g_kg: null, cec_cmol_kg: null },
  { depth: "5-15cm", phh2o: null, clay_pct: null, sand_pct: null, silt_pct: null, soc_g_kg: null, nitrogen_g_kg: null, cec_cmol_kg: null },
  { depth: "15-30cm", phh2o: null, clay_pct: null, sand_pct: null, silt_pct: null, soc_g_kg: null, nitrogen_g_kg: null, cec_cmol_kg: null },
];

type FieldKey = Exclude<keyof SoilDepthLayer, "depth">;

const TEXTURE_LABEL_KEY: Record<SoilTexture, string> = {
  sand: "setup.textureSand",
  sandy_loam: "setup.textureSandyLoam",
  loam: "setup.textureLoam",
  silt_loam: "setup.textureSiltLoam",
  clay_loam: "setup.textureClayLoam",
  clay: "setup.textureClay",
};

export function StepSoil({ location, override, onChange }: StepSoilProps) {
  const { t } = useI18n();
  const [layers, setLayers] = useState<SoilDepthLayer[] | null>(override);
  const [loading, setLoading] = useState(!override);
  const [error, setError] = useState<string | null>(null);
  const [needsManual, setNeedsManual] = useState(false);
  const [editing, setEditing] = useState(false);

  const [presets, setPresets] = useState<SoilPreset[] | null>(null);
  const [appliedTexture, setAppliedTexture] = useState<SoilTexture | null>(null);

  useEffect(() => {
    if (override) return; // user already has edited values for this session
    let cancelled = false;
    // Starting a new data fetch -- reset loading/error state for it.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    setError(null);
    api
      .soil(location)
      .then((res) => {
        if (cancelled) return;
        if (res.status === "manual_input_needed" || res.status === "unavailable") {
          setLayers(EMPTY_LAYERS);
          setNeedsManual(true);
          setEditing(true);
        } else {
          setLayers(res.layers);
          setNeedsManual(false);
        }
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : t("states.errorDesc"));
        setLayers(EMPTY_LAYERS);
        setNeedsManual(true);
        setEditing(true);
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.lat, location.lon, override]);

  useEffect(() => {
    if (!needsManual || presets) return;
    api
      .soilPresets()
      .then((res) => setPresets(res.presets))
      .catch(() => setPresets(null));
  }, [needsManual, presets]);

  function applyPreset(texture: SoilTexture) {
    const preset = presets?.find((p) => p.texture === texture);
    if (!preset) return;
    const next = EMPTY_LAYERS.map((layer) => ({
      ...layer,
      phh2o: preset.phh2o,
      clay_pct: preset.clay_pct,
      sand_pct: preset.sand_pct,
      silt_pct: preset.silt_pct,
      soc_g_kg: preset.soc_g_kg,
      nitrogen_g_kg: preset.nitrogen_g_kg,
      cec_cmol_kg: preset.cec_cmol_kg,
    }));
    setLayers(next);
    setAppliedTexture(texture);
    onChange(next);
  }

  function updateField(depthIndex: number, field: FieldKey, value: string) {
    if (!layers) return;
    setAppliedTexture(null);
    const next = layers.map((layer, i) =>
      i === depthIndex ? { ...layer, [field]: value === "" ? null : Number.parseFloat(value) } : layer
    );
    setLayers(next);
    onChange(next);
  }

  const fields: { key: FieldKey; label: string; step?: string }[] = [
    { key: "phh2o", label: t("setup.soilPh"), step: "0.1" },
    { key: "clay_pct", label: t("setup.soilClay") },
    { key: "sand_pct", label: t("setup.soilSand") },
    { key: "silt_pct", label: t("setup.soilSilt") },
    { key: "soc_g_kg", label: t("setup.soilSoc") },
    { key: "nitrogen_g_kg", label: t("setup.soilNitrogen") },
    { key: "cec_cmol_kg", label: t("setup.soilCec") },
  ];

  const depthLabels: Record<string, string> = {
    "0-5cm": t("setup.soilDepth05"),
    "5-15cm": t("setup.soilDepth515"),
    "15-30cm": t("setup.soilDepth1530"),
  };

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-semibold text-foreground">{t("setup.soilTitle")}</h2>
        <p className="mt-1 text-sm text-muted-foreground">{t("setup.soilDesc")}</p>
      </div>

      {error && !loading && <ErrorState description={error} />}

      {needsManual && !loading && (
        <div className="space-y-3">
          <div className="flex items-start gap-3 rounded-lg border border-warning/30 bg-warning/10 px-4 py-3 text-sm">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
            <p>{t("setup.soilManualNeeded")}</p>
          </div>

          <div className="rounded-lg border border-border p-4">
            <div className="flex items-center gap-2">
              <Sprout className="h-4 w-4 text-crop" />
              <Label className="text-sm font-medium text-foreground">{t("setup.chooseSoilType")}</Label>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">{t("setup.chooseSoilTypeDesc")}</p>
            <Select value={appliedTexture ?? undefined} onValueChange={(v) => applyPreset(v as SoilTexture)} disabled={!presets}>
              <SelectTrigger className="mt-3 w-full sm:w-64">
                <SelectValue placeholder={presets ? t("setup.chooseSoilType") : t("common.loading")} />
              </SelectTrigger>
              <SelectContent>
                {presets?.map((preset) => (
                  <SelectItem key={preset.texture} value={preset.texture}>
                    {t(TEXTURE_LABEL_KEY[preset.texture])}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      )}

      {!loading && layers && (
        <div className="flex flex-wrap items-center justify-between gap-2">
          {appliedTexture ? (
            <Badge variant="outline" className="gap-1.5 border-crop/40 text-crop">
              <Sprout className="h-3 w-3" />
              {t("setup.estimatedFromSoilType", { texture: t(TEXTURE_LABEL_KEY[appliedTexture]) })}
            </Badge>
          ) : (
            <span />
          )}
          <Button variant="outline" size="sm" className="gap-1.5" onClick={() => setEditing((e) => !e)}>
            {editing ? <Check className="h-3.5 w-3.5" /> : <Pencil className="h-3.5 w-3.5" />}
            {editing ? t("setup.soilDoneEditing") : t("setup.soilEditToggle")}
          </Button>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {loading
          ? Array.from({ length: 3 }).map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-4 w-20" />
                </CardHeader>
                <CardContent className="space-y-2">
                  {Array.from({ length: 7 }).map((__, j) => (
                    <Skeleton key={j} className="h-6 w-full" />
                  ))}
                </CardContent>
              </Card>
            ))
          : layers?.map((layer, depthIndex) => (
              <Card key={layer.depth}>
                <CardHeader>
                  <CardTitle className="text-sm">{depthLabels[layer.depth] ?? layer.depth}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2.5">
                  {fields.map((field) => (
                    <div key={field.key} className="flex items-center justify-between gap-2">
                      <Label htmlFor={`${layer.depth}-${field.key}`} className="text-xs text-muted-foreground">
                        {field.label}
                      </Label>
                      {editing ? (
                        <Input
                          id={`${layer.depth}-${field.key}`}
                          type="number"
                          step={field.step ?? "1"}
                          value={layer[field.key] ?? ""}
                          onChange={(e) => updateField(depthIndex, field.key, e.target.value)}
                          className="h-7 w-20 text-right text-sm"
                        />
                      ) : (
                        <Badge variant="secondary" className="font-mono">
                          {layer[field.key] ?? "—"}
                        </Badge>
                      )}
                    </div>
                  ))}
                </CardContent>
              </Card>
            ))}
      </div>
    </div>
  );
}
