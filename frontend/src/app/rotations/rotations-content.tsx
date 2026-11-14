"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { AgronomistPanel } from "@/components/agronomist/agronomist-panel";
import { RotationCard } from "@/components/rotations/rotation-card";
import { RotationCompare } from "@/components/rotations/rotation-compare";
import { RotationFilters, type RotationFilter, type RotationSort } from "@/components/rotations/rotation-filters";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { RotationGridSkeleton } from "@/components/shared/loading-skeletons";
import { Card, CardContent } from "@/components/ui/card";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { useFarmAnalysis } from "@/hooks/use-farm-analysis";
import { useCrops } from "@/hooks/use-crops";
import { useI18n } from "@/i18n";
import { rotationKey } from "@/lib/rotation-key";
import type { ScoredRotation, StressedRotationResult } from "@/types/api";

const SORT_FIELD: Record<RotationSort, (r: ScoredRotation) => number> = {
  score: (r) => r.priority_weighted_score_0_100,
  water: (r) => r.sub_scores.water_fit,
  soil: (r) => r.sub_scores.soil_health,
  heat: (r) => r.sub_scores.heat_risk,
};

export function RotationsContent() {
  const { t } = useI18n();
  const router = useRouter();
  const { data, status, error, hasFarm, retry } = useFarmAnalysis();
  const crops = useCrops();

  const [filter, setFilter] = useState<RotationFilter>("top");
  const [sort, setSort] = useState<RotationSort>("score");
  const [selected, setSelected] = useState<string[]>([]);
  const [compareOpen, setCompareOpen] = useState(false);
  const [detailsRotation, setDetailsRotation] = useState<ScoredRotation | null>(null);

  const stressByKey = useMemo(() => {
    const map = new Map<string, StressedRotationResult>();
    if (data?.stress_test) {
      for (const result of data.stress_test.results) {
        map.set(rotationKey(result.rotation), result);
      }
    }
    return map;
  }, [data]);

  const list = useMemo(() => {
    if (!data?.rotations) return [];
    const base = filter === "top" ? data.rotations.top : data.rotations.pareto_optimal;
    return [...base].sort((a, b) => SORT_FIELD[sort](b) - SORT_FIELD[sort](a));
  }, [data, filter, sort]);

  const selectedRotations = list.filter((r) => selected.includes(rotationKey(r.rotation)));

  function toggleSelect(key: string) {
    setSelected((prev) => {
      if (prev.includes(key)) return prev.filter((k) => k !== key);
      if (prev.length >= 2) return [prev[1], key];
      return [...prev, key];
    });
  }

  if (!hasFarm && status !== "loading") {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6 lg:px-8">
        <EmptyState
          title={t("states.noDataYet")}
          description={t("states.emptyDesc")}
          actionLabel={t("states.goToSetup")}
          onAction={() => router.push("/setup")}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">{t("rotations.title")}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("rotations.subtitle")}</p>
        {data?.rotations && (
          <p className="mt-1 text-xs text-muted-foreground">
            {t("rotations.candidatesEvaluated", { count: data.rotations.candidates_evaluated })}
          </p>
        )}
      </div>

      {status === "loading" && (
        <div className="space-y-6">
          <p className="text-sm text-muted-foreground">{t("states.loadingFarm")}</p>
          <RotationGridSkeleton />
        </div>
      )}

      {status === "error" && <ErrorState description={error ?? undefined} onRetry={retry} />}

      {status === "ready" && data?.rotations && (
        <div className="space-y-5">
          <RotationFilters filter={filter} onFilterChange={setFilter} sort={sort} onSortChange={setSort} />

          {selected.length > 0 && (
            <Card className="border-primary/30 bg-primary/5">
              <CardContent className="flex items-center justify-between py-3 text-sm">
                <span>{t("rotations.compareSelected", { count: selected.length })}</span>
                <div className="flex gap-2">
                  {selected.length === 2 && (
                    <button
                      type="button"
                      className="font-medium text-primary underline-offset-4 hover:underline"
                      onClick={() => setCompareOpen(true)}
                    >
                      {t("rotations.compareBtn")}
                    </button>
                  )}
                  <button
                    type="button"
                    className="text-muted-foreground underline-offset-4 hover:underline"
                    onClick={() => setSelected([])}
                  >
                    {t("rotations.clearCompare")}
                  </button>
                </div>
              </CardContent>
            </Card>
          )}

          {list.length === 0 ? (
            <EmptyState title={t("rotations.noResults")} />
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {list.map((rotation) => {
                const key = rotationKey(rotation.rotation);
                return (
                  <RotationCard
                    key={key}
                    rotation={rotation}
                    crops={crops}
                    stressResult={stressByKey.get(key)}
                    isSelected={selected.includes(key)}
                    onToggleSelect={() => toggleSelect(key)}
                    compareDisabled={selected.length >= 2}
                    onViewDetails={() => setDetailsRotation(rotation)}
                  />
                );
              })}
            </div>
          )}

          <RotationCompare open={compareOpen} onOpenChange={setCompareOpen} rotations={selectedRotations} crops={crops} />

          <Sheet open={!!detailsRotation} onOpenChange={(open) => !open && setDetailsRotation(null)}>
            <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-md">
              <div className="p-5">
                <AgronomistPanel rotation={detailsRotation} crops={crops} />
              </div>
            </SheetContent>
          </Sheet>
        </div>
      )}
    </div>
  );
}
