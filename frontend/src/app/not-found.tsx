import Link from "next/link";
import { EmptyState } from "@/components/shared/empty-state";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-24 sm:px-6 lg:px-8">
      <EmptyState title="404 — page not found" description="This page doesn't exist." />
      <div className="mt-6 text-center">
        <Link href="/" className="text-sm font-medium text-primary underline-offset-4 hover:underline">
          Back to home
        </Link>
      </div>
    </div>
  );
}
