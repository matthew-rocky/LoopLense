import { Network } from "lucide-react";
import { PageShell } from "@/components/layout/page-shell";
import { NetworkWorkspace } from "@/components/network/network-workspace";
import { EmptyState } from "@/components/ui/empty-state";
import { getLoops, getNetwork } from "@/lib/api";
import { loopId } from "@/lib/format";

export default async function NetworkPage({ searchParams }: { searchParams: Promise<{ loop?: string }> }) {
  const params = await searchParams;
  try {
    const loops = await getLoops({ limit: 50 });
    const loop = params.loop ?? loopId(loops[0] ?? {});
    const graph = loop ? await getNetwork(loop) : undefined;
    return (
      <PageShell className="h-[calc(100vh-2rem)]">
        <header>
          <p className="text-sm font-semibold uppercase tracking-wide text-[var(--accent)]">Network view</p>
          <h1 className="mt-2 text-4xl font-bold">Interactive Transfer Graph</h1>
          <p className="mt-3 text-[var(--muted)]">Nodes show organization names. BN, location, and evidence metadata remain available in hover context.</p>
        </header>
        <NetworkWorkspace initialLoopId={loop} initialGraph={graph} loopOptions={loops} />
      </PageShell>
    );
  } catch {
    return (
      <PageShell>
        <EmptyState icon={Network} title="Network unavailable" description="Start the FastAPI backend on port 8000 and refresh this page." />
      </PageShell>
    );
  }
}
