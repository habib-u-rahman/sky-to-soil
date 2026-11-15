"use client";

import { Droplets, Leaf, Repeat, ShieldAlert, Wallet } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { useI18n } from "@/i18n";
import type { Priorities } from "@/types/api";

interface StepPrioritiesProps {
  value: Priorities;
  onChange: (value: Priorities) => void;
}

interface PriorityDef {
  key: keyof Omit<Priorities, "income_proxy">;
  icon: LucideIcon;
  label: string;
  desc: string;
}

export function StepPriorities({ value, onChange }: StepPrioritiesProps) {
  const { t } = useI18n();

  const priorities: PriorityDef[] = [
    { key: "save_water", icon: Droplets, label: t("setup.prioritySaveWater"), desc: t("setup.prioritySaveWaterDesc") },
    { key: "build_soil", icon: Leaf, label: t("setup.priorityBuildSoil"), desc: t("setup.priorityBuildSoilDesc") },
    { key: "lower_climate_risk", icon: ShieldAlert, label: t("setup.priorityLowerRisk"), desc: t("setup.priorityLowerRiskDesc") },
    { key: "stay_close_to_current", icon: Repeat, label: t("setup.priorityStayClose"), desc: t("setup.priorityStayCloseDesc") },
  ];

  function setValue(key: keyof Priorities, v: number) {
    onChange({ ...value, [key]: v });
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-heading text-2xl font-semibold text-foreground">{t("setup.prioritiesTitle")}</h2>
        <p className="mt-1 text-sm text-muted-foreground">{t("setup.prioritiesDesc")}</p>
      </div>

      <div className="space-y-5">
        {priorities.map((p) => (
          <div key={p.key} className="rounded-lg border border-border p-4">
            <div className="flex items-center gap-3">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
                <p.icon className="h-4 w-4" />
              </span>
              <div className="flex-1">
                <Label className="text-sm font-medium text-foreground">{p.label}</Label>
                <p className="text-xs text-muted-foreground">{p.desc}</p>
              </div>
              <span className="w-10 shrink-0 text-end text-sm font-mono text-muted-foreground">
                {Math.round(value[p.key] * 100)}%
              </span>
            </div>
            <Slider
              className="mt-4"
              value={[value[p.key] * 100]}
              onValueChange={(v) => setValue(p.key, (Array.isArray(v) ? v[0] : v) / 100)}
              min={0}
              max={100}
              step={5}
            />
          </div>
        ))}

        <div className="rounded-lg border border-border p-4">
          <div className="flex items-center gap-3">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Wallet className="h-4 w-4" />
            </span>
            <div className="flex-1">
              <Label className="text-sm font-medium text-foreground">
                {t("setup.priorityIncome")} <span className="text-muted-foreground">({t("common.optional")})</span>
              </Label>
              <p className="text-xs text-muted-foreground">{t("setup.priorityIncomeDesc")}</p>
            </div>
            <Switch
              checked={value.income_proxy !== null}
              onCheckedChange={(checked) => onChange({ ...value, income_proxy: checked ? 0.25 : null })}
            />
          </div>
          {value.income_proxy !== null && (
            <>
              <div className="mt-3 flex items-center justify-end">
                <span className="w-10 shrink-0 text-end text-sm font-mono text-muted-foreground">
                  {Math.round(value.income_proxy * 100)}%
                </span>
              </div>
              <Slider
                className="mt-1"
                value={[value.income_proxy * 100]}
                onValueChange={(v) => onChange({ ...value, income_proxy: (Array.isArray(v) ? v[0] : v) / 100 })}
                min={0}
                max={100}
                step={5}
              />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
