import { Suspense } from "react";
import { MemoPageClient } from "@/components/memo/memo-page-client";

export default function MemoPage() {
  return (
    <Suspense fallback={null}>
      <MemoPageClient />
    </Suspense>
  );
}
