import { Suspense } from "react";
import { RotationGridSkeleton } from "@/components/shared/loading-skeletons";
import { RotationsContent } from "./rotations-content";

export default function RotationsPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
          <RotationGridSkeleton />
        </div>
      }
    >
      <RotationsContent />
    </Suspense>
  );
}
