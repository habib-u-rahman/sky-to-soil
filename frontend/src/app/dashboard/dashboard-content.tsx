"use client";

import { ArrowRight, Pencil } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";
import { AnalysisProgress } from "@/components/dashboard/analysis-progress";
import { ClimateKpiGrid } from "@/components/dashboard/climate-kpis";
import { HotDaysChart, RainfallChart, RootZoneWetnessChart, TemperatureChart, TrendSignals } from "@/components/dashboard/climate-charts";
import { NdviChart, NdviYearOverYearChart } from "@/components/dashboard/ndvi-chart";
import { SoilProfileCard } from "@/components/dashboard/soil-profile-card";
import { ExportButton } from "@/components/export/export-button";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { ChartCardSkeleton, KpiGridSkeleton } from "@/components/shared/loading-skeletons";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useI18n } from "@/i18n";
import { useFarmAnalysis } from "@/hooks/use-farm-analysis";
import { allCurrentCrops, useFarmStore } from "@/lib/farm-store";

export function DashboardContent() {
  const { t } = useI18n();
  const router = useRouter();
  const searchParams = useSearchParams();
  const loadDemoFarm = useFarmStore((s) => s.loadDemoFarm);
  const hasLocation = useFarmStore((s) => !!s.location);
  const currentCrops = useFarmStore((s) => s.currentCrops);

  useEffect(() => {
    if (searchParams.get("demo") === "true" && !hasLocation) {
      loadDemoFarm();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const { data, status, error, hasFarm, retry, isDemo } = useFarmAnalysis();

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
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-heading text-3xl font-semibold tracking-tight text-foreground">{t("dashboard.title")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{t("dashboard.subtitle")}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" render={<Link href="/setup" />} className="gap-1.5">
            <Pencil className="h-3.5 w-3.5" />
            {t("dashboard.editFarm")}
          </Button>
          {data && <ExportButton data={data} currentCrops={allCurrentCrops(currentCrops)} isDemo={isDemo} />}
          <Button size="sm" render={<Link href="/rotations" />} className="gap-1.5">
            {t("dashboard.viewRotations")}
            <ArrowRight className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {status === "loading" && isDemo && (
        <div className="space-y-6">
          <p className="text-sm text-muted-foreground">{t("states.loadingFarm")}</p>
          <KpiGridSkeleton />
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <ChartCardSkeleton />
            <ChartCardSkeleton />
          </div>
          <Skeleton className="h-64 w-full" />
        </div>
      )}

      {/* A live (non-demo) analysis genuinely takes ~70s, plus up to ~60s
          more if Render's free tier has to wake from a cold start -- show
          staged progress instead of an indefinite skeleton so this doesn't
          read as frozen. */}
      {status === "loading" && !isDemo && <AnalysisProgress />}

      {status === "error" && <ErrorState description={error ?? undefined} onRetry={retry} />}

      {status === "ready" && data && (
        <div className="space-y-6">
          {data.warnings.length > 0 && (
            <div className="rounded-lg border border-warning/30 bg-warning/10 px-4 py-3 text-sm">
              <p className="font-medium text-foreground">{t("states.partialDataTitle")}</p>
              <ul className="mt-1 list-inside list-disc space-y-0.5 text-muted-foreground">
                {data.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {data.climate ? (
            <ClimateKpiGrid climate={data.climate} t={t} />
          ) : (
            <EmptyState title={t("states.emptyTitle")} description={t("states.errorDesc")} />
          )}

          {data.climate && (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <TemperatureChart climate={data.climate} />
              <RootZoneWetnessChart climate={data.climate} />
              <HotDaysChart climate={data.climate} />
              <RainfallChart climate={data.climate} />
              <TrendSignals climate={data.climate} />
            </div>
          )}

          {data.ndvi && <NdviChart ndvi={data.ndvi} />}
          {data.ndvi && <NdviYearOverYearChart ndvi={data.ndvi} />}

          {data.soil && <SoilProfileCard soil={data.soil} />}
        </div>
      )}
    </div>
  );
}
