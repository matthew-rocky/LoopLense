import { AlertTriangle, CheckCircle2, ShieldQuestion } from "lucide-react";
import type { AnyRow } from "@/lib/types";
import { text } from "@/lib/format";

function tone(status: string) {
  const low = status.toLowerCase();
  if (low.includes("pass") || low.includes("support") || low.includes("verified")) return { icon: CheckCircle2, cls: "text-[var(--success)]" };
  if (low.includes("fail") || low.includes("mismatch") || low.includes("blocked")) return { icon: AlertTriangle, cls: "text-[var(--danger)]" };
  return { icon: ShieldQuestion, cls: "text-[var(--warning)]" };
}

export function VerificationCards({ verification }: { verification?: AnyRow | null }) {
  if (!verification) return null;
  const checks = Array.isArray(verification.checks) ? (verification.checks as AnyRow[]) : [];
  const status = text(verification.overall_status ?? verification.final_status ?? verification.status ?? "Needs review");
  return (
    <section className="mt-4 rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-xs uppercase text-[var(--muted)]">Verification</div>
          <h3 className="mt-1 text-lg font-semibold">{status}</h3>
        </div>
        <div className="rounded-full border border-[var(--border)] px-3 py-1 text-xs text-[var(--muted)]">{text(verification.rows_used_count ?? 0)} rows checked</div>
      </div>
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
    </section>
  );
}

