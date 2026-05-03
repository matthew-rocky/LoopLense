import type { AnyRow } from "@/lib/types";
import { text } from "@/lib/format";

function columns(rows: AnyRow[]) {
  const preferred = ["loop_id", "review_label", "review_score", "total_flow", "circular_flow", "participant_count", "name", "bn", "source_name", "target_name"];
  const keys = Array.from(new Set(rows.flatMap((row) => Object.keys(row))));
  return [...preferred.filter((key) => keys.includes(key)), ...keys.filter((key) => !preferred.includes(key))].slice(0, 7);
}

export function DataTable({ rows, title = "Returned Data" }: { rows?: AnyRow[]; title?: string }) {
  const safeRows = rows ?? [];
  if (!safeRows.length) return null;
  const cols = columns(safeRows);
  return (
    <section className="mt-4 overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface-muted)]">
      <div className="border-b border-[var(--border)] px-4 py-3 text-sm font-semibold">{title}</div>
      <div className="max-h-72 overflow-auto table-scroll">
        <table className="w-full min-w-[720px] text-left text-xs">
          <thead className="sticky top-0 z-10 bg-[var(--surface-strong)] text-[var(--muted)]">
            <tr>
              {cols.map((col) => (
                <th key={col} className="px-4 py-2 font-semibold uppercase">{col.replaceAll("_", " ")}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border)]">
            {safeRows.slice(0, 12).map((row, index) => (
              <tr key={index} className="hover:bg-[var(--surface-muted)]">
                {cols.map((col) => (
                  <td key={col} className="max-w-64 px-4 py-2 text-[var(--muted)]">
                    <span className="line-clamp-2">{text(row[col])}</span>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

