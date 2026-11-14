"use client";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useI18n } from "@/i18n";

export type RotationFilter = "top" | "pareto";
export type RotationSort = "score" | "water" | "soil" | "heat";

interface RotationFiltersProps {
  filter: RotationFilter;
  onFilterChange: (value: RotationFilter) => void;
  sort: RotationSort;
  onSortChange: (value: RotationSort) => void;
}

export function RotationFilters({ filter, onFilterChange, sort, onSortChange }: RotationFiltersProps) {
  const { t } = useI18n();

  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <Tabs value={filter} onValueChange={(v) => onFilterChange(v as RotationFilter)}>
        <TabsList>
          <TabsTrigger value="top">{t("rotations.filterAll")}</TabsTrigger>
          <TabsTrigger value="pareto">{t("rotations.filterPareto")}</TabsTrigger>
        </TabsList>
      </Tabs>

      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">{t("rotations.sortBy")}</span>
        <Select value={sort} onValueChange={(v) => onSortChange(v as RotationSort)}>
          <SelectTrigger className="h-8 w-40 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="score">{t("rotations.sortScore")}</SelectItem>
            <SelectItem value="water">{t("rotations.sortWater")}</SelectItem>
            <SelectItem value="soil">{t("rotations.sortSoil")}</SelectItem>
            <SelectItem value="heat">{t("rotations.sortHeat")}</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
