"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Network } from "lucide-react";
import { PageShell } from "@/components/layout/page-shell";
import { NetworkWorkspace } from "@/components/network/network-workspace";
import { EmptyState } from "@/components/ui/empty-state";
import { getLoops, getNetwork } from "@/lib/api";
import { loopId } from "@/lib/format";
import type { AnyRow, NetworkGraph } from "@/lib/types";

export function NetworkPageClient() {
  const searchParams = useSearchParams();
  const selected = searchParams.get("loop") ?? undefined;
  const [loops, setLoops] = useState<AnyRow[]>([]);
  const [graph, setGraph] = useState<NetworkGraph | undefined>();
  const [initialLoopId, setInitialLoopId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const nextLoops = await getLoops({ limit: 50 });
        const nextLoop = selected ?? loopId(nextLoops[0] ?? {});
        const nextGraph = nextLoop ? await getNetwork(nextLoop) : undefined;
        if (!active) return;
        setLoops(nextLoops);
        setInitialLoopId(nextLoop);
        setGraph(nextGraph);
      } catch {
        if (active) setError(true);
      } finally {
        if (active) setLoading(false);
      }
    }
    load();
    return () => {
      active = false;
    };
  }, [selected]);

  if (error) {
    return (
      <PageShell>
        <EmptyState icon={Network} title="Network unavailable" description="Start the FastAPI backend on port 8000 and refresh this page." />
      </PageShell>
    );
  }

  return (
    <PageShell className="h-[calc(100vh-2rem)]">
      <header>
        <p className="text-sm font-semibold uppercase tracking-wide text-[var(--accent)]">Network view</p>
        <h1 className="mt-2 text-4xl font-bold">Interactive Transfer Graph</h1>
        <p className="mt-3 text-[var(--muted)]">Nodes show organization names. BN, location, and evidence metadata remain available in hover context.</p>
      </header>
      {loading ? <EmptyState icon={Network} title="Loading network" description="Loading transfer graph data." /> : <NetworkWorkspace initialLoopId={initialLoopId} initialGraph={graph} loopOptions={loops} />}
    </PageShell>
  );
}
