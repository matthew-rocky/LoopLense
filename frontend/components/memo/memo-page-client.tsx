"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { FileCheck } from "lucide-react";
import { MemoWorkspace } from "@/components/memo/memo-workspace";
import { PageShell } from "@/components/layout/page-shell";
import { EmptyState } from "@/components/ui/empty-state";
import { getLoops } from "@/lib/api";
import { loopId } from "@/lib/format";
import type { AnyRow } from "@/lib/types";

export function MemoPageClient() {
  const searchParams = useSearchParams();
  const selected = searchParams.get("loop") ?? undefined;
  const [loops, setLoops] = useState<AnyRow[]>([]);
  const [initialLoopId, setInitialLoopId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    getLoops({ limit: 50 })
      .then((nextLoops) => {
        if (!active) return;
        setLoops(nextLoops);
        setInitialLoopId(selected ?? loopId(nextLoops[0] ?? {}));
      })
      .catch(() => {
        if (active) setError(true);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [selected]);

  if (error) {
    return (
      <PageShell>
        <EmptyState icon={FileCheck} title="Memo workspace unavailable" description="Start the FastAPI backend on port 8000 and refresh this page." />
      </PageShell>
    );
  }

  return (
    <PageShell>
      <header>
        <p className="text-sm font-semibold uppercase tracking-wide text-[var(--accent)]">Memo and verification</p>
        <h1 className="mt-2 text-4xl font-bold">Evidence Review Workspace</h1>
        <p className="mt-3 max-w-3xl text-[var(--muted)]">Generate a neutral memo, inspect verification, copy or download a markdown version, and keep safety wording bounded.</p>
      </header>
      {loading ? <EmptyState icon={FileCheck} title="Loading memo workspace" description="Loading loop options." /> : <MemoWorkspace initialLoopId={initialLoopId} loopOptions={loops} />}
    </PageShell>
  );
}
