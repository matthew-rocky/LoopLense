import { MemoWorkspace } from "@/components/memo/memo-workspace";
import { PageShell } from "@/components/layout/page-shell";
import { EmptyState } from "@/components/ui/empty-state";
import { getLoops } from "@/lib/api";
import { loopId } from "@/lib/format";
import { FileCheck } from "lucide-react";

export default async function MemoPage({ searchParams }: { searchParams: Promise<{ loop?: string }> }) {
  const params = await searchParams;
  try {
    const loops = await getLoops({ limit: 50 });
    const initialLoopId = params.loop ?? loopId(loops[0] ?? {});
    return (
      <PageShell>
        <header>
          <p className="text-sm font-semibold uppercase tracking-wide text-[var(--accent)]">Memo and verification</p>
          <h1 className="mt-2 text-4xl font-bold">Evidence Review Workspace</h1>
          <p className="mt-3 max-w-3xl text-[var(--muted)]">Generate a neutral memo, inspect verification, copy or download a markdown version, and keep safety wording bounded.</p>
        </header>
        <MemoWorkspace initialLoopId={initialLoopId} loopOptions={loops} />
      </PageShell>
    );
  } catch {
    return (
      <PageShell>
        <EmptyState icon={FileCheck} title="Memo workspace unavailable" description="Start the FastAPI backend on port 8000 and refresh this page." />
      </PageShell>
    );
  }
}
