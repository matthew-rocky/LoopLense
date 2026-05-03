import { Search } from "lucide-react";
import { PageShell } from "@/components/layout/page-shell";
import { LoopsTable } from "@/components/loops/loops-table";
import { EmptyState } from "@/components/ui/empty-state";
import { getLoops } from "@/lib/api";

export default async function LoopsPage() {
  try {
    const rows = await getLoops({ limit: 1000 });
    return (
      <PageShell className="h-[calc(100vh-2rem)]">
        <header className="flex flex-col justify-between gap-3 lg:flex-row lg:items-end">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-[var(--accent)]">Loop explorer</p>
            <h1 className="mt-2 text-4xl font-bold">Full-Screen Circular Pattern Table</h1>
          </div>
          <p className="max-w-2xl text-sm leading-6 text-[var(--muted)]">
            Search by loop ID, organization name, account name, BN, label, score, or participant. Tables expand to the available monitor space.
          </p>
        </header>
        <LoopsTable rows={rows} />
      </PageShell>
    );
  } catch {
    return (
      <PageShell>
        <EmptyState icon={Search} title="Loop data unavailable" description="Start the FastAPI backend on port 8000 and refresh this page." />
      </PageShell>
    );
  }
}
