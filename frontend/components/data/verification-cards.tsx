import { AlertTriangle, CheckCircle2, ShieldQuestion } from "lucide-react";
import type { AnyRow } from "@/lib/types";
import { text } from "@/lib/format";

function tone(status: string) {
  const low = status.toLowerCase();
  if (low.includes("fail") || low.includes("mismatch") || low.includes("blocked")) return { icon: AlertTriangle, cls: "text-[var(--danger)]" };
  if (low.includes("unsupported") || low.includes("warning") || low.includes("needs review") || low.includes("partial") || low.includes("not found")) return { icon: ShieldQuestion, cls: "text-[var(--warning)]" };
  if (low.includes("pass") || low.includes("verified") || low.includes("supported")) return { icon: CheckCircle2, cls: "text-[var(--success)]" };
  return { icon: ShieldQuestion, cls: "text-[var(--warning)]" };
}

export function VerificationCards({ verification }: { verification?: AnyRow | null }) {
  if (!verification) return null;
  const checks = Array.isArray(verification.checks) ? (verification.checks as AnyRow[]) : [];
  const status = text(verification.overall_status ?? verification.final_status ?? verification.status ?? "Needs review");
  const ToneIcon = tone(status).icon;
  return (
    <details className="mt-4 rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-4">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
        <span className="inline-flex items-center gap-2 text-sm font-semibold">
          <ToneIcon size={17} className={tone(status).cls} />
          Grounding checks: {status}
        </span>
        <span className="text-xs text-[var(--muted)]">Verification details</span>
      </summary>
      <div className="mt-3 rounded-full border border-[var(--border)] px-3 py-1 text-xs text-[var(--muted)] w-fit">{text(verification.rows_used_count ?? 0)} rows checked</div>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {checks.slice(0, 6).map((check, index) => {
          const statusText = text(check.status ?? "Needs review");
          const ToneIcon = tone(statusText).icon;
          return (
            <article key={index} className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3">
              <div className="flex items-start gap-2">
                <ToneIcon size={17} className={tone(statusText).cls} />
                <div>
                  <div className="text-sm font-semibold">{statusText}</div>
                  <p className="mt-1 line-clamp-3 text-xs leading-5 text-[var(--muted)]">{text(check.claim ?? check.check ?? check.explanation)}</p>
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </details>
  );
}

