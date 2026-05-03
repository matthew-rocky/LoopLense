"use client";

import { useMemo, useState } from "react";
import type { ComponentType } from "react";
import Link from "next/link";
import { Bot, ChevronDown, ExternalLink, Network, Search } from "lucide-react";
import type { AnyRow } from "@/lib/types";
import { loopId, money, score, text } from "@/lib/format";
import { Badge } from "@/components/ui/badge";

type SortKey = "score" | "flow" | "participants" | "loop";

function participantNames(row: AnyRow): string[] {
  return Array.isArray(row.participant_names) ? row.participant_names.map(String).filter(Boolean) : [];
}

function participantCount(row: AnyRow): number {
  const count = Number(row.participant_count);
  return Number.isFinite(count) ? count : participantNames(row).length;
}

function participantPreview(row: AnyRow): string {
  const names = participantNames(row);
  if (names.length === 0) return "No participant names available";
  const shown = names.slice(0, 3);
  const remaining = names.length - shown.length;
  return `${shown.join(", ")}${remaining > 0 ? `, +${remaining} more` : ""}`;
}

function num(value: unknown) {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

export function LoopsTable({ rows }: { rows: AnyRow[] }) {
  const [search, setSearch] = useState("");
  const [label, setLabel] = useState("");
  const [minScore, setMinScore] = useState("");
  const [minFlow, setMinFlow] = useState("");
  const [sort, setSort] = useState<SortKey>("score");
  const [page, setPage] = useState(1);
  const pageSize = 80;

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return rows
      .filter((row) => {
        const labelOk = !label || row.review_label === label || row.label === label;
        const scoreOk = !minScore || num(row.review_score ?? row.score) >= num(minScore);
        const flowOk = !minFlow || num(row.circular_flow ?? row.total_flow) >= num(minFlow);
        const searchOk = !q || JSON.stringify(row).toLowerCase().includes(q);
        return labelOk && scoreOk && flowOk && searchOk;
      })
      .sort((a, b) => {
        if (sort === "flow") return num(b.circular_flow ?? b.total_flow) - num(a.circular_flow ?? a.total_flow);
        if (sort === "participants") return participantCount(b) - participantCount(a);
        if (sort === "loop") return loopId(a).localeCompare(loopId(b), undefined, { numeric: true });
        return num(b.review_score ?? b.score) - num(a.review_score ?? a.score);
      });
  }, [rows, search, label, minScore, minFlow, sort]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const visible = filtered.slice((page - 1) * pageSize, page * pageSize);

  return (
    <div className="flex h-[calc(100vh-8.5rem)] min-h-[680px] flex-col overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)]">
      <div className="sticky top-0 z-20 border-b border-[var(--border)] bg-[var(--surface-strong)] p-4 backdrop-blur">
        <div className="grid gap-3 xl:grid-cols-[1fr_150px_130px_150px_150px]">
          <label className="relative">
            <Search className="absolute left-3 top-3 text-[var(--muted)]" size={18} />
            <input
              className="w-full rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] py-2.5 pl-10 pr-3 text-sm outline-none focus:focus-ring"
              placeholder="Search loop ID, BN, legal name, account name, label, or participant"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setPage(1);
              }}
            />
          </label>
          <Select value={label} onChange={setLabel} options={[["", "All labels"], ["High", "High"], ["Medium", "Medium"], ["Low", "Low"]]} />
          <input className="rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] px-3 py-2.5 text-sm outline-none focus:focus-ring" placeholder="Min score" value={minScore} onChange={(event) => setMinScore(event.target.value)} />
          <input className="rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] px-3 py-2.5 text-sm outline-none focus:focus-ring" placeholder="Min flow" value={minFlow} onChange={(event) => setMinFlow(event.target.value)} />
          <Select value={sort} onChange={(value) => setSort(value as SortKey)} options={[["score", "Sort: Score"], ["flow", "Sort: Flow"], ["participants", "Sort: Participants"], ["loop", "Sort: Loop"]]} />
        </div>
        <div className="mt-3 flex items-center justify-between text-xs text-[var(--muted)]">
          <span>{filtered.length.toLocaleString()} matching loops</span>
          <span>Showing {visible.length.toLocaleString()} rows</span>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto table-scroll">
        <table className="w-full min-w-[1180px] border-collapse text-left text-sm">
          <thead className="sticky top-0 z-10 border-b border-[var(--border)] bg-[var(--surface-strong)] text-xs uppercase text-[var(--muted)]">
            <tr>
              <th className="px-4 py-3">Loop</th>
              <th className="px-4 py-3">Label</th>
              <th className="px-4 py-3">Score</th>
              <th className="px-4 py-3">Circular Flow</th>
              <th className="px-4 py-3">Participants</th>
              <th className="px-4 py-3">Why Flagged</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border)]">
            {visible.map((row) => (
              <tr key={loopId(row)} className="group transition hover:bg-[var(--surface-muted)]">
                <td className="px-4 py-4 font-semibold text-[var(--accent)]">
                  <Link href={`/loops/${encodeURIComponent(loopId(row))}`}>Loop {loopId(row)}</Link>
                </td>
                <td className="px-4 py-4"><Badge label={row.review_label ?? row.label} /></td>
                <td className="px-4 py-4">{score(row.review_score ?? row.score)}</td>
                <td className="px-4 py-4">{money(row.circular_flow ?? row.total_flow)}</td>
                <td className="px-4 py-4">
                  <details className="group/details">
                    <summary className="flex cursor-pointer list-none items-start gap-2">
                      <span className="max-w-xl leading-6">{participantPreview(row)}</span>
                      <ChevronDown size={15} className="mt-1 shrink-0 text-[var(--muted)] transition group-open/details:rotate-180" />
                    </summary>
                    <div className="mt-3 grid gap-2">
                      {participantNames(row).map((name, index) => (
                        <div key={`${name}-${index}`} className="rounded-lg bg-[var(--surface-muted)] px-3 py-2 text-xs">{name}</div>
                      ))}
                    </div>
                  </details>
                  <span className="mt-2 inline-flex rounded-full border border-[var(--border)] bg-[var(--surface-muted)] px-2 py-0.5 text-xs text-[var(--muted)]">
                    {participantCount(row)} participants
                  </span>
                </td>
                <td className="max-w-lg px-4 py-4 text-[var(--muted)]"><span className="line-clamp-3">{text(row.why_flagged)}</span></td>
                <td className="px-4 py-4">
                  <div className="flex gap-2">
                    <Action href={`/loops/${encodeURIComponent(loopId(row))}`} title="View details" icon={ExternalLink} />
                    <Action href={`/network?loop=${encodeURIComponent(loopId(row))}`} title="Open network" icon={Network} />
                    <Action href={`/chat?loop=${encodeURIComponent(loopId(row))}`} title="Ask about this loop" icon={Bot} />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between border-t border-[var(--border)] bg-[var(--surface-strong)] px-4 py-3 text-sm">
        <button className="rounded-md border border-[var(--border)] px-3 py-1.5 disabled:opacity-40" disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>Previous</button>
        <span className="text-[var(--muted)]">Page {page} of {totalPages}</span>
        <button className="rounded-md border border-[var(--border)] px-3 py-1.5 disabled:opacity-40" disabled={page >= totalPages} onClick={() => setPage((current) => Math.min(totalPages, current + 1))}>Next</button>
      </div>
    </div>
  );
}

function Select({ value, onChange, options }: { value: string; onChange: (value: string) => void; options: [string, string][] }) {
  return (
    <select className="rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] px-3 py-2.5 text-sm outline-none focus:focus-ring" value={value} onChange={(event) => onChange(event.target.value)}>
      {options.map(([optionValue, label]) => <option key={optionValue} value={optionValue}>{label}</option>)}
    </select>
  );
}

function Action({ href, title, icon: Icon }: { href: string; title: string; icon: ComponentType<{ size?: number }> }) {
  return (
    <Link title={title} href={href} className="grid h-9 w-9 place-items-center rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] text-[var(--muted)] transition hover:bg-[var(--surface)] hover:text-[var(--foreground)]">
      <Icon size={16} />
    </Link>
  );
}
