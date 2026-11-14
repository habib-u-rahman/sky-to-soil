import { RotationGridSkeleton } from "@/components/shared/loading-skeletons";

export default function RotationsLoading() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
      <RotationGridSkeleton />
    </div>
  );
}
