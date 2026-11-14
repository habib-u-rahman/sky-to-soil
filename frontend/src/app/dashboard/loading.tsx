import { ChartCardSkeleton, KpiGridSkeleton } from "@/components/shared/loading-skeletons";

export default function DashboardLoading() {
  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-10 sm:px-6 lg:px-8">
      <KpiGridSkeleton />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ChartCardSkeleton />
        <ChartCardSkeleton />
      </div>
    </div>
  );
}
