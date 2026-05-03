"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type { ComponentType } from "react";
import { useSearchParams } from "next/navigation";
import { Bot, FileText, Network, Search, ShieldCheck } from "lucide-react";
import { PageShell } from "@/components/layout/page-shell";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { getLoop } from "@/lib/api";
import { money, text, score } from "@/lib/format";
import type { LoopDetail } from "@/lib/types";

function rows(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null) : [];
}

function routeLoopId() {
  if (typeof window === "undefined") return "";
  const parts = window.location.pathname.split("/").filter(Boolean);
  return parts[0] === "loops" && parts[1] && parts[1] !== "detail" ? decodeURIComponent(parts[1]) : "";
}

export function LoopDetailClient() {
  const searchParams = useSearchParams();
  const id = useMemo(() => searchParams.get("loop") ?? routeLoopId(), [searchParams]);
  const [detail, setDetail] = useState<LoopDetail | null>(null);
  const [loading, setLoading] = useState(Boolean(id));
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) {
      setLoading(false);
      setError("Select a loop from the loop explorer.");
      return;
    }
    let active = true;
    setLoading(true);
    setError("");
    getLoop(id)
      .then((result) => {
        if (active) setDetail(result);
      })
      .catch(() => {
        if (active) setError("The loop could not be loaded. Confirm the backend is running and the loop ID exists.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [id]);

  if (loading) {
    return (
      <PageShell>
        <EmptyState icon={Search} title="Loading loop" description="Loading loop evidence and transfer records." />
      </PageShell>
    );
  }

  if (error || !detail) {
    return (
      <PageShell>
        <EmptyState icon={Search} title="Loop unavailable" description={error || "The loop could not be loaded."} />
      </PageShell>
    );
  }

  const loop = detail.loop;
  const participants = rows(detail.people);
  const edges = rows(detail.edges);
  return (
    <PageShell>
      <header className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-[var(--accent)]">Loop detail</p>
          <h1 className="mt-2 text-4xl font-bold">Loop {id}</h1>
          <p className="mt-3 max-w-3xl text-[var(--muted)]">Organization names, transfer edges, participant positions, and deterministic review-priority context.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Action href={`/memo?loop=${encodeURIComponent(id)}`} icon={FileText} label="Generate Memo" />
          <Action href={`/network?loop=${encodeURIComponent(id)}`} icon={Network} label="Open Network" />
          <Action href={`/chat?loop=${encodeURIComponent(id)}`} icon={Bot} label="Ask LoopLens" />
        </div>
      </header>
      <div className="grid gap-4 md:grid-cols-4">
        <Card><div className="text-sm text-[var(--muted)]">Review label</div><div className="mt-4"><Badge label={loop.review_label} /></div></Card>
        <Card><div className="text-sm text-[var(--muted)]">Review score</div><div className="mt-3 text-3xl font-bold">{score(loop.review_score)}</div></Card>
        <Card><div className="text-sm text-[var(--muted)]">Circular flow</div><div className="mt-3 text-3xl font-bold">{money(loop.circular_flow ?? loop.total_flow)}</div></Card>
        <Card><div className="text-sm text-[var(--muted)]">Participants</div><div className="mt-3 text-3xl font-bold">{text(loop.participant_count)}</div></Card>
      </div>
      <Card>
        <h2 className="flex items-center gap-2 text-lg font-semibold"><ShieldCheck size={18} />Score Explanation</h2>
        <p className="mt-3 leading-7 text-[var(--muted)]">{text(detail.score_explanation.why_flagged)}</p>
        <div className="mt-4 grid gap-3 md:grid-cols-4">
          <Mini label="Min year" value={text(loop.min_year)} />
          <Mini label="Max year" value={text(loop.max_year)} />
          <Mini label="Bottleneck" value={money(loop.bottleneck_amt)} />
          <Mini label="Government indicator" value={text(loop.loop_max_govt_share_pct)} />
        </div>
      </Card>
      <Card>
        <h2 className="text-lg font-semibold">Organizations In This Loop</h2>
        <div className="mt-4 overflow-auto rounded-xl border border-[var(--border)] table-scroll">
          <table className="w-full min-w-[980px] text-left text-sm">
            <thead className="sticky top-0 bg-[var(--surface-strong)] text-xs uppercase text-[var(--muted)]">
              <tr><th className="px-4 py-3">Organization</th><th className="px-4 py-3">BN</th><th className="px-4 py-3">Location</th><th className="px-4 py-3">Position</th><th className="px-4 py-3">Sends To</th><th className="px-4 py-3">Receives From</th></tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {participants.map((person) => (
                <tr key={String(person.bn)} className="align-top hover:bg-[var(--surface-muted)]">
                  <td className="px-4 py-3 font-semibold text-[var(--accent)]">{text(person.name ?? person.legal_name ?? person.account_name)}</td>
                  <td className="px-4 py-3 text-[var(--muted)]">{text(person.bn)}</td>
                  <td className="px-4 py-3 text-[var(--muted)]">{[person.city, person.province].filter(Boolean).map(String).join(", ") || "n/a"}</td>
                  <td className="px-4 py-3 text-[var(--muted)]">{text(person.position_in_loop)}</td>
                  <td className="px-4 py-3 text-[var(--muted)]">{text(person.sends_to)}<div className="text-xs opacity-70">{text(person.sends_to_bn)}</div></td>
                  <td className="px-4 py-3 text-[var(--muted)]">{text(person.receives_from)}<div className="text-xs opacity-70">{text(person.receives_from_bn)}</div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
      <Card>
        <h2 className="text-lg font-semibold">Transfer Edges</h2>
        <div className="mt-4 max-h-[520px] overflow-auto rounded-xl border border-[var(--border)] table-scroll">
          <table className="w-full min-w-[860px] text-left text-sm">
            <thead className="sticky top-0 bg-[var(--surface-strong)] text-xs uppercase text-[var(--muted)]">
              <tr><th className="px-4 py-3">From</th><th className="px-4 py-3">To</th><th className="px-4 py-3">Amount</th><th className="px-4 py-3">Years</th></tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {edges.slice(0, 80).map((edge, index) => (
                <tr key={index} className="hover:bg-[var(--surface-muted)]">
                  <td className="px-4 py-3 text-[var(--muted)]">{text(edge.source_name ?? edge.src_name)}<div className="text-xs opacity-70">{text(edge.source_bn ?? edge.src)}</div></td>
                  <td className="px-4 py-3 text-[var(--muted)]">{text(edge.target_name ?? edge.dst_name)}<div className="text-xs opacity-70">{text(edge.target_bn ?? edge.dst)}</div></td>
                  <td className="px-4 py-3">{money(edge.total_amt ?? edge.amount)}</td>
                  <td className="px-4 py-3 text-[var(--muted)]">{text(edge.years ?? edge.min_year)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </PageShell>
  );
}

function Action({ href, icon: Icon, label }: { href: string; icon: ComponentType<{ size?: number; className?: string }>; label: string }) {
  return (
    <Link className="rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] px-3 py-2 text-sm font-semibold transition hover:-translate-y-0.5 hover:bg-[var(--surface)]" href={href}>
      <Icon className="mr-2 inline" size={16} />
      {label}
    </Link>
  );
}

function Mini({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-3">
      <div className="text-xs uppercase text-[var(--muted)]">{label}</div>
      <div className="mt-1 font-semibold">{value}</div>
    </div>
  );
}
