import { Suspense } from "react";
import { NetworkPageClient } from "@/components/network/network-page-client";

export default function NetworkPage() {
  return (
    <Suspense fallback={null}>
      <NetworkPageClient />
    </Suspense>
  );
}
