"use client";

import { useMemo, useState } from "react";
import { Clipboard, Download, FileCheck, Loader2, TriangleAlert } from "lucide-react";
import { postMemo, postVerify } from "@/lib/api";
import type { AnyRow, MemoResponse } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { MemoDocument } from "@/components/data/memo-document";
import { VerificationCards } from "@/components/data/verification-cards";
import { loopId, text } from "@/lib/format";

export function MemoWorkspace({ initialLoopId, loopOptions = [] }: { initialLoopId: string; loopOptions?: AnyRow[] }) {
  const [loopIdValue, setLoopIdValue] = useState(initialLoopId);
  const [memo, setMemo] = useState<MemoResponse | null>(null);
  const [verification, setVerification] = useState<{ final_status: string; verification: AnyRow; warnings: string[] } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const memoText = useMemo(() => {
    if (!memo) return "";
    const doc = memo.memo;
    return [
      `# ${text(doc.title ?? "Review-priority memo")}`,
      "",
      text(doc.summary),
      "",
      "## Findings",
      ...(Array.isArray(doc.findings) ? doc.findings.map((item) => `- ${String(item)}`) : []),
      "",
      "## Rationale",
      text(doc.rationale),
      "",
      "## Next Steps",
      ...(Array.isArray(doc.next_steps) ? doc.next_steps.map((item) => `- ${String(item)}`) : []),
      "",
      text(doc.disclaimer ?? memo.disclaimer)
    ].join("\n");
  }, [memo]);

  async function generate() {
    if (!loopIdValue.trim() || loading) return;
    setLoading(true);
    setError("");
    try {
      const result = await postMemo(loopIdValue.trim());
      setMemo(result);
      const verify = await postVerify(loopIdValue.trim(), result.memo);
      setVerification(verify);
    } catch {
      setError("Could not reach the LoopLens API. Confirm the FastAPI backend is running on port 8000.");
    } finally {
      setLoading(false);
    }
  }

  function downloadMemo() {
    const blob = new Blob([memoText], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `looplens-memo-${loopIdValue || "loop"}.md`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="grid min-h-[calc(100vh-12rem)] gap-5 xl:grid-cols-[1.1fr_.9fr]">
      <Card className="overflow-hidden">
        <div className="mb-4 grid gap-3 md:grid-cols-[1fr_auto_auto_auto]">
          <input
            className="rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] px-3 py-2 text-sm outline-none focus:focus-ring"
            value={loopIdValue}
            onChange={(event) => setLoopIdValue(event.target.value)}
            list="memo-loop-options"
            placeholder="Loop ID"
          />
          <datalist id="memo-loop-options">
            {loopOptions.map((row) => <option key={loopId(row)} value={loopId(row)}>{Array.isArray(row.participant_names) ? row.participant_names.slice(0, 2).join(", ") : loopId(row)}</option>)}
          </datalist>
          <Button onClick={generate} disabled={loading}>
            {loading ? <Loader2 className="animate-spin" size={16} /> : <FileCheck size={16} />}
            Generate
          </Button>
          <Button className="bg-[var(--surface-muted)] text-[var(--foreground)]" disabled={!memoText} onClick={() => navigator.clipboard.writeText(memoText)}>
            <Clipboard size={16} />
            Copy
          </Button>
          <Button className="bg-[var(--surface-muted)] text-[var(--foreground)]" disabled={!memoText} onClick={downloadMemo}>
            <Download size={16} />
            Download
          </Button>
        </div>
        {error && <div className="mb-4 rounded-xl border border-red-400/30 bg-red-400/10 p-3 text-sm text-[var(--danger)]">{error}</div>}
        {memo ? (
          <MemoDocument memo={memo.memo} disclaimer={memo.disclaimer} />
        ) : (
          <div className="grid min-h-96 place-items-center rounded-xl border border-dashed border-[var(--border)] bg-[var(--surface-muted)] p-10 text-center text-[var(--muted)]">
            <div>
              <FileCheck className="mx-auto text-[var(--accent)]" size={36} />
              <h2 className="mt-4 text-xl font-semibold text-[var(--foreground)]">Generate a neutral evidence memo</h2>
              <p className="mt-2 max-w-md text-sm leading-6">Select a loop ID, generate an evidence-based memo, then review claim-level verification beside it.</p>
            </div>
          </div>
        )}
      </Card>
      <Card>
        <h2 className="text-lg font-semibold">Verification Panel</h2>
        {verification ? (
          <>
            <VerificationCards verification={verification.verification} />
            {verification.warnings.length > 0 && (
              <section className="mt-4 rounded-xl border border-amber-400/30 bg-amber-400/10 p-4">
                <div className="mb-3 flex items-center gap-2 font-semibold text-[var(--warning)]">
                  <TriangleAlert size={18} />
                  Warnings
                </div>
                <div className="space-y-2">
                  {verification.warnings.slice(0, 8).map((warning, index) => (
                    <div key={index} className="rounded-lg bg-[var(--surface)] px-3 py-2 text-sm text-[var(--muted)]">{warning}</div>
                  ))}
                </div>
              </section>
            )}
          </>
        ) : (
          <p className="mt-4 text-sm leading-6 text-[var(--muted)]">Claim-level verification appears here after memo generation. Unsupported or risky wording is flagged for human review.</p>
        )}
      </Card>
    </div>
  );
}
