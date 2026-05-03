"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { ComponentType } from "react";
import { Bot, FileText, Network, Search, ShieldCheck } from "lucide-react";
import { DashboardCharts } from "@/components/dashboard/dashboard-charts";
import { MetricCard } from "@/components/dashboard/metric-card";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { PageShell } from "@/components/layout/page-shell";
import { getLoops, getSummary } from "@/lib/api";
import { loopId, money, number, score, text } from "@/lib/format";
import type { AnyRow, Summary } from "@/lib/types";

function names(row: Record<string, unknown>) {
  return Array.isArray(row.participant_names) ? row.participant_names.map(String).slice(0, 3).join(", ") : "";
}

export function DashboardPageClient() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loops, setLoops] = useState<AnyRow[]>([]);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.all([getSummary(), getLoops({ limit: 600 })])
      .then(([nextSummary, nextLoops]) => {
        if (!active) return;
        setSummary(nextSummary);
        setLoops(nextLoops);
      })
      .catch(() => {
        if (active) setError(true);
      });
    return () => {
      active = false;
    };
  }, []);

  if (error) {
    return (
      <PageShell>
        <EmptyState icon={ShieldCheck} title="Backend unavailable" description="Start the FastAPI backend on port 8000, then refresh the dashboard." />
      </PageShell>
    );
  }

  if (!summary) {
    return (
      <PageShell>
        <EmptyState icon={ShieldCheck} title="Loading dashboard" description="Loading review metrics and chart data." />
      </PageShell>
    );
  }

  const high = summary.review_label_distribution.find((item) => item.review_label === "High")?.count ?? 0;
  const medium = summary.review_label_distribution.find((item) => item.review_label === "Medium")?.count ?? 0;
  const low = summary.review_label_distribution.find((item) => item.review_label === "Low")?.count ?? 0;
  return (
    <PageShell>
      <section className="grid gap-5 xl:grid-cols-[1.35fr_.65fr]">
        <Card className="relative overflow-hidden p-7">
          <div className="absolute right-8 top-8 h-28 w-28 rounded-full bg-[var(--accent)]/15 blur-2xl" />
          <p className="text-sm font-semibold uppercase tracking-wide text-[var(--accent)]">Executive AI review dashboard</p>
          <h1 className="mt-3 max-w-4xl text-4xl font-bold tracking-normal lg:text-6xl">Circular funding intelligence for human review</h1>
          <p className="mt-4 max-w-3xl text-base leading-7 text-[var(--muted)]">LoopLens ranks circular charity funding patterns, enriches them with organization names, and keeps every answer grounded in loaded records.</p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Action href="/loops" icon={Search} label="Open Loop Explorer" />
            <Action href="/network" icon={Network} label="Open Network View" />
            <Action href="/chat" icon={Bot} label="Ask LoopLens" />
            <Action href="/memo" icon={FileText} label="Generate Memo" />
          </div>
        </Card>
        <Card className="flex flex-col justify-between">
          <div className="flex items-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-xl bg-[var(--surface-muted)] text-[var(--accent)]"><ShieldCheck size={22} /></div>
            <div><h2 className="font-semibold">Responsible Use</h2><p className="text-sm text-[var(--muted)]">Not a finding of wrongdoing.</p></div>
          </div>
          <p className="mt-5 text-sm leading-6 text-[var(--muted)]">Scores and labels are review-priority indicators. Reviewers should inspect source records and context before taking action.</p>
        </Card>
      </section>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Total loops" value={number(summary.total_loops)} helper="Loaded circular patterns" />
        <MetricCard label="High review priority" value={number(high)} helper="Earlier review candidates" />
        <MetricCard label="Medium priority" value={number(medium)} helper="Queue candidates" />
        <MetricCard label="Circular flow" value={money(summary.total_circular_flow)} helper={summary.flow_column ?? "Available flow field"} />
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <Card><div className="text-sm text-[var(--muted)]">High</div><div className="mt-2 text-3xl font-bold text-amber-500">{number(high)}</div></Card>
        <Card><div className="text-sm text-[var(--muted)]">Medium</div><div className="mt-2 text-3xl font-bold text-sky-500">{number(medium)}</div></Card>
        <Card><div className="text-sm text-[var(--muted)]">Low</div><div className="mt-2 text-3xl font-bold text-emerald-500">{number(low)}</div></Card>
      </div>
      <DashboardCharts loops={loops} labels={summary.review_label_distribution} />
      <Card>
        <div className="mb-4 flex items-center justify-between"><h2 className="text-lg font-semibold">Top Review-Priority Loops</h2><Link href="/loops" className="text-sm font-semibold text-[var(--accent)]">View all</Link></div>
        <div className="grid gap-3 2xl:grid-cols-2">
          {summary.top_high_priority_loops.slice(0, 8).map((row) => (
            <Link key={loopId(row)} href={`/loops/detail?loop=${encodeURIComponent(loopId(row))}`} className="group flex items-center justify-between gap-4 rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-4 transition hover:-translate-y-0.5 hover:bg-[var(--surface)]">
              <div className="min-w-0">
                <div className="font-semibold text-[var(--accent)]">Loop {loopId(row)}</div>
                {names(row) && <div className="mt-1 truncate text-sm">{names(row)}</div>}
                <div className="mt-1 line-clamp-2 text-xs text-[var(--muted)]">{text(row.why_flagged)}</div>
              </div>
              <div className="flex shrink-0 items-center gap-3"><Badge label={row.review_label} /><span className="text-sm text-[var(--muted)]">{score(row.review_score)}</span></div>
            </Link>
          ))}
        </div>
      </Card>
    </PageShell>
  );
}

function Action({ href, icon: Icon, label }: { href: string; icon: ComponentType<{ size?: number }>; label: string }) {
  return <Link href={href} className="inline-flex items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] px-4 py-2 text-sm font-semibold transition hover:-translate-y-0.5 hover:bg-[var(--surface)]"><Icon size={16} />{label}</Link>;
}
