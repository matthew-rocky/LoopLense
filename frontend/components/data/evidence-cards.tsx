import { Database, MapPin } from "lucide-react";
import type { ReactNode } from "react";
import type { AnyRow } from "@/lib/types";
import { money, score, text } from "@/lib/format";

function evidenceTitle(row: AnyRow) {
  return text(row.name ?? row.legal_name ?? row.account_name ?? row.charity ?? row.loop_id ?? row.bn ?? "Evidence row");
}

export function EvidenceCards({ rows }: { rows?: AnyRow[] }) {
  const safeRows = (rows ?? []).slice(0, 4);
  if (!safeRows.length) return null;
  return (
    <div className="mt-4 grid gap-3 md:grid-cols-2">
      {safeRows.map((row, index) => (
        <article key={index} className="rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-4">
          <div className="flex items-start gap-3">
            <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[var(--surface)] text-[var(--accent)]">
              <Database size={17} />
            </div>
            <div className="min-w-0">
              <h4 className="truncate text-sm font-semibold">{evidenceTitle(row)}</h4>
              <div className="mt-1 text-xs text-[var(--muted)]">{text(row.bn ?? row.loop_id ?? row.review_label ?? row.stat)}</div>
            </div>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
            {row.review_score !== undefined && <Metric label="Score" value={score(row.review_score)} />}
            {(row.total_flow !== undefined || row.circular_flow !== undefined) && <Metric label="Flow" value={money(row.circular_flow ?? row.total_flow)} />}
            {row.participant_count !== undefined && <Metric label="Participants" value={text(row.participant_count)} />}
            {(row.city !== undefined || row.province !== undefined) && (
              <Metric label="Location" value={<span className="inline-flex items-center gap-1"><MapPin size={12} />{[row.city, row.province].filter(Boolean).map(String).join(", ")}</span>} />
            )}
          </div>
        </article>
      ))}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-lg bg-[var(--surface)] px-3 py-2">
      <div className="text-[10px] uppercase text-[var(--muted)]">{label}</div>
      <div className="mt-1 font-semibold">{value}</div>
    </div>
  );
}
