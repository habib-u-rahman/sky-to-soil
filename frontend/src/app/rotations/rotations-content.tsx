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
import { allCurrentCrops } from "@/lib/farm-store";
import { useFarmStore } from "@/lib/farm-store";
import { rotationKey } from "@/lib/rotation-key";
import type { RotationId, ScoredRotation, StressedRotationResult } from "@/types/api";

const SORT_FIELD: Record<RotationSort, (r: ScoredRotation) => number> = {
  score: (r) => r.priority_weighted_score_0_100,
  water: (r) => r.sub_scores.water_fit,
  soil: (r) => r.sub_scores.soil_health,
  heat: (r) => r.sub_scores.heat_risk,
};

interface ListedRotation {
  id: RotationId;
  rotation: ScoredRotation;
}

export function RotationsContent() {
  const { t } = useI18n();
  const router = useRouter();
  const { data, status, error, hasFarm, retry, isDemo } = useFarmAnalysis();
  const crops = useCrops();
  const currentCrops = useFarmStore((s) => s.currentCrops);

  const [filter, setFilter] = useState<RotationFilter>("top");
  const [sort, setSort] = useState<RotationSort>("score");
  const [selected, setSelected] = useState<string[]>([]);
  const [compareOpen, setCompareOpen] = useState(false);
  const [detailsRotation, setDetailsRotation] = useState<ListedRotation | null>(null);

  const stressByKey = useMemo(() => {
    const map = new Map<string, StressedRotationResult>();
    if (data?.stress_test) {
      for (const result of data.stress_test.results) {
        map.set(rotationKey(result.rotation), result);
      }
    }
    return map;
  }, [data]);

  // rotation_id (e.g. "top_3") must reflect the ORIGINAL index in
  // rotations.top / .pareto_optimal -- the backend resolves it that way --
  // so it's computed here, before the display-only sort below.
  const list = useMemo<ListedRotation[]>(() => {
    if (!data?.rotations) return [];
    const prefix = filter === "top" ? "top" : "pareto";
    const base = filter === "top" ? data.rotations.top : data.rotations.pareto_optimal;
    const withIds = base.map((rotation, index) => ({ id: `${prefix}_${index}`, rotation }));
    return withIds.sort((a, b) => SORT_FIELD[sort](b.rotation) - SORT_FIELD[sort](a.rotation));
  }, [data, filter, sort]);

  const selectedRotations = list.filter((r) => selected.includes(rotationKey(r.rotation.rotation))).map((r) => r.rotation);

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
              {list.map((item) => {
                const key = rotationKey(item.rotation.rotation);
                return (
                  <RotationCard
                    key={item.id}
                    rotation={item.rotation}
                    crops={crops}
                    stressResult={stressByKey.get(key)}
                    isSelected={selected.includes(key)}
                    onToggleSelect={() => toggleSelect(key)}
                    compareDisabled={selected.length >= 2}
                    onViewDetails={() => setDetailsRotation(item)}
                  />
                );
              })}
            </div>
          )}

          <RotationCompare open={compareOpen} onOpenChange={setCompareOpen} rotations={selectedRotations} crops={crops} />

          <Sheet open={!!detailsRotation} onOpenChange={(open) => !open && setDetailsRotation(null)}>
            <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-lg">
              <div className="p-5">
                {detailsRotation && data && (
                  <AgronomistPanel
                    rotationId={detailsRotation.id}
                    rotation={detailsRotation.rotation}
                    crops={crops}
                    analysis={data}
                    currentCrops={allCurrentCrops(currentCrops)}
                    isDemo={isDemo}
                  />
                )}
              </div>
            </SheetContent>
          </Sheet>
        </div>
      )}
    </div>
  );
}
