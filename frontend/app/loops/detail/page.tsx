import { Suspense } from "react";
import { LoopDetailClient } from "@/components/loops/loop-detail-client";

export default function LoopDetailPage() {
  return (
    <Suspense fallback={null}>
      <LoopDetailClient />
    </Suspense>
  );
}
