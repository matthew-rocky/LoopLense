import type { AnyRow } from "@/lib/types";
import { text } from "@/lib/format";

function list(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String).filter(Boolean) : [];
}

export function MemoDocument({ memo, disclaimer }: { memo?: AnyRow | null; disclaimer?: string }) {
  if (!memo) return null;
  return (
    <article className="rounded-2xl border border-[var(--border)] bg-[var(--surface-strong)] p-6 leading-7 shadow-sm">
      <div className="mb-5 border-b border-[var(--border)] pb-4">
        <div className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">Evidence-based review memo</div>
        <h2 className="mt-2 text-2xl font-bold">{text(memo.title ?? "Review-priority memo")}</h2>
      </div>
      <p className="text-[var(--foreground)]">{text(memo.summary)}</p>
      {list(memo.findings).length > 0 && (
        <>
          <h3 className="mt-6 font-semibold">Findings</h3>
          <ul className="mt-2 space-y-2">
            {list(memo.findings).map((item, index) => <li key={index} className="rounded-lg bg-[var(--surface-muted)] px-3 py-2 text-sm">{item}</li>)}
          </ul>
        </>
      )}
      {memo.rationale && (
        <>
          <h3 className="mt-6 font-semibold">Rationale</h3>
          <p className="mt-2 text-sm text-[var(--muted)]">{text(memo.rationale)}</p>
        </>
      )}
      {list(memo.next_steps).length > 0 && (
        <>
          <h3 className="mt-6 font-semibold">Next Steps</h3>
          <ul className="mt-2 list-disc space-y-2 pl-5 text-sm text-[var(--muted)]">
            {list(memo.next_steps).map((item, index) => <li key={index}>{item}</li>)}
          </ul>
        </>
      )}
      <div className="mt-6 rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-3 text-sm text-[var(--muted)]">
        {text(disclaimer ?? memo.disclaimer ?? "This memo is not a finding of wrongdoing.")}
      </div>
    </article>
  );
}
