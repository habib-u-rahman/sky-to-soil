import { Suspense } from "react";
import { DashboardContent } from "./dashboard-content";
import { KpiGridSkeleton } from "@/components/shared/loading-skeletons";

export default function DashboardPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
          <KpiGridSkeleton />
        </div>
      }
    >
      <DashboardContent />
    </Suspense>
  );
}
