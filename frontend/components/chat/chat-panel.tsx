"use client";

import { useEffect, useState } from "react";
import type { ComponentType } from "react";
import { AlertCircle, Bot, FileText, GitBranch, Loader2, Send, Sparkles, User, Users } from "lucide-react";
import { motion } from "framer-motion";
import { postChat } from "@/lib/api";
import type { AnyRow, ChatResponse } from "@/lib/types";
import { loopId, money, score, text } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ChartRenderer } from "@/components/data/chart-renderer";
import { DataTable } from "@/components/data/data-table";
import { EvidenceCards } from "@/components/data/evidence-cards";
import { MemoDocument } from "@/components/data/memo-document";
import { VerificationCards } from "@/components/data/verification-cards";

const prompts = [
  "Why was this loop flagged?",
  "Show the participants in the selected loop.",
  "Generate a neutral memo for this loop.",
  "Which loop has the largest circular flow?",
  "Show review label distribution."
];

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  response?: ChatResponse & { memo?: AnyRow; memo_verification?: AnyRow };
  error?: string;
};

export function ChatPanel({ selectedLoopId }: { selectedLoopId?: string }) {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeLoopId, setActiveLoopId] = useState(selectedLoopId);

  useEffect(() => {
    if (selectedLoopId) setActiveLoopId(selectedLoopId);
  }, [selectedLoopId]);

  async function ask(text: string) {
    const prompt = text.trim();
    if (!prompt || loading) return;
    const userMessage: Message = { id: crypto.randomUUID(), role: "user", content: prompt };
    setMessages((current) => [...current, userMessage]);
    setLoading(true);
    setMessage("");
    try {
      const response = await postChat(prompt, activeLoopId);
      const returnedLoopId = response.selected_loop_id ?? firstLoopId(response.data);
      if (returnedLoopId) setActiveLoopId(returnedLoopId);
      setMessages((current) => [
        ...current,
        { id: crypto.randomUUID(), role: "assistant", content: response.answer, response }
      ]);
    } catch {
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: "I could not reach the LoopLens API. Confirm the FastAPI backend is running on port 8000, then try again.",
          error: "Backend unavailable"
        }
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-[calc(100vh-10rem)] min-h-[680px] flex-col overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)]">
      <div className="border-b border-[var(--border)] bg-[var(--surface-strong)] p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold text-[var(--accent)]">
              <Sparkles size={16} />
              Evidence-grounded assistant
            </div>
            {activeLoopId && <div className="mt-1 inline-flex rounded-full border border-[var(--border)] px-2 py-1 text-xs text-[var(--muted)]">Current loop context: {activeLoopId}</div>}
          </div>
          <div className="flex flex-wrap gap-2">
            {prompts.map((prompt) => (
              <motion.button
                key={prompt}
                whileHover={{ y: -2 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => ask(prompt)}
                className="rounded-full border border-[var(--border)] bg-[var(--surface-muted)] px-3 py-1.5 text-xs text-[var(--foreground)] transition hover:bg-[var(--surface)]"
              >
                {prompt}
              </motion.button>
            ))}
          </div>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto p-4 table-scroll">
        {messages.length === 0 && (
          <Card className="mx-auto mt-12 max-w-3xl text-center">
            <div className="mx-auto grid h-12 w-12 place-items-center rounded-xl bg-[var(--surface-muted)] text-[var(--accent)]">
              <Bot size={22} />
            </div>
            <h2 className="mt-4 text-xl font-semibold">Ask about loops, participants, memos, or charts</h2>
            <p className="mt-2 text-sm leading-6 text-[var(--muted)]">Responses are based on loaded data and include evidence, tables, charts, and verification where available.</p>
          </Card>
        )}
        <div className="space-y-5">
          {messages.map((item) => (
            <MessageBubble key={item.id} message={item} onAsk={ask} />
          ))}
          {loading && (
            <div className="flex items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-4 text-sm text-[var(--muted)]">
              <Loader2 className="animate-spin" size={18} />
              LoopLens is checking the loaded records...
            </div>
          )}
        </div>
      </div>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          ask(message);
        }}
        className="border-t border-[var(--border)] bg-[var(--surface-strong)] p-3"
      >
        <div className="flex gap-2 rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-2">
          <input
            className="flex-1 bg-transparent px-3 text-sm outline-none"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Ask about loaded loops, participant names, circular flow, or neutral memos"
          />
          <Button disabled={loading}>
            {loading ? <Loader2 className="animate-spin" size={16} /> : <Send size={16} />}
            Ask
          </Button>
        </div>
      </form>
    </div>
  );
}

function firstLoopId(rows?: AnyRow[]) {
  const first = rows?.[0];
  if (!first) return undefined;
  const id = first.loop_id ?? first.id ?? first.cycle_id ?? first.component_id;
  return id === null || id === undefined || id === "" ? undefined : String(id);
}

function MessageBubble({ message, onAsk }: { message: Message; onAsk: (text: string) => void }) {
  const assistant = message.role === "assistant";
  return (
    <motion.article initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className={`flex gap-3 ${assistant ? "justify-start" : "justify-end"}`}>
      {assistant && <Avatar icon={message.error ? AlertCircle : Bot} />}
      <div className={`max-w-[min(920px,92%)] rounded-2xl border border-[var(--border)] p-4 ${assistant ? "bg-[var(--surface-muted)]" : "bg-[var(--accent)] text-[var(--accent-foreground)]"}`}>
        <p className="whitespace-pre-wrap leading-7">{message.content}</p>
        {message.response && <AssistantResponse response={message.response} onAsk={onAsk} />}
      </div>
      {!assistant && <Avatar icon={User} />}
    </motion.article>
  );
}

function Avatar({ icon: Icon }: { icon: ComponentType<{ size?: number }> }) {
  return (
    <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl border border-[var(--border)] bg-[var(--surface)] text-[var(--accent)]">
      <Icon size={17} />
    </div>
  );
}

function AssistantResponse({ response, onAsk }: { response: ChatResponse & { memo?: AnyRow; memo_verification?: AnyRow }; onAsk: (text: string) => void }) {
  const unsupported = response.intent === "unsupported";
  const loopRow = response.loop ?? (response.data.length === 1 ? response.data[0] : undefined);
  const orgRows = organizationRows(response);
  return (
    <>
      {!unsupported && loopRow ? <LoopSummaryCard row={loopRow} /> : null}
      {!unsupported && orgRows.length ? <OrganizationDetailsCard rows={orgRows} /> : null}
      {!unsupported && <ChartRenderer chart={response.chart} rows={response.data} />}
      {!unsupported && response.memo ? <MemoDocument memo={response.memo} /> : null}
      {!unsupported && !orgRows.length && <EvidenceCards rows={response.evidence} />}
      {!unsupported ? <QuickActions onAsk={onAsk} /> : null}
      <FollowupChips followups={response.suggested_followups} onAsk={onAsk} />
      {!unsupported && response.data.length ? (
        <details className="mt-4 rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-4">
          <summary className="cursor-pointer text-sm font-semibold">View returned records</summary>
          <DataTable rows={response.data} title="Returned records" />
        </details>
      ) : null}
      {!unsupported && <VerificationCards verification={response.memo_verification ?? response.verification} />}
      {!unsupported && process.env.NODE_ENV !== "production" && (
        <details className="mt-4 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3 text-xs text-[var(--muted)]">
          <summary className="cursor-pointer font-semibold">Show raw response</summary>
          <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap">{JSON.stringify(response, null, 2)}</pre>
        </details>
      )}
    </>
  );
}

function organizationRows(response: ChatResponse) {
  const rows = response.participants?.length ? response.participants : response.evidence ?? [];
  const seen = new Set<string>();
  return rows.filter((row) => {
    const key = text(row.bn ?? row.BN ?? row.business_number ?? row.registration_number ?? row.name ?? row.legal_name ?? row.organization_name);
    const isOrganization = Boolean(row.name ?? row.organization_name ?? row.legal_name ?? row.charity_name ?? row.account_name ?? row.bn ?? row.business_number);
    if (!isOrganization || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function LoopSummaryCard({ row }: { row: AnyRow }) {
  return (
    <section className="mt-4 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-xs uppercase text-[var(--muted)]">Loop summary</div>
          <h3 className="mt-1 text-lg font-semibold">Loop {loopId(row)}</h3>
        </div>
        <div className="rounded-full border border-[var(--border)] px-3 py-1 text-xs text-[var(--muted)]">{text(row.review_label ?? row.label ?? "Review label n/a")}</div>
      </div>
      <div className="mt-4 grid gap-2 sm:grid-cols-3">
        <SummaryMetric label="Score" value={score(row.review_score ?? row.score)} />
        <SummaryMetric label="Circular flow" value={money(row.total_flow ?? row.circular_flow ?? row.score_total_flow)} />
        <SummaryMetric label="Participants" value={text(row.participant_count)} />
      </div>
      {row.why_flagged ? <p className="mt-3 text-sm leading-6 text-[var(--muted)]">{text(row.why_flagged)}</p> : null}
    </section>
  );
}

function SummaryMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] px-3 py-2">
      <div className="text-[10px] uppercase text-[var(--muted)]">{label}</div>
      <div className="mt-1 text-sm font-semibold">{value}</div>
    </div>
  );
}

function OrganizationDetailsCard({ rows }: { rows: AnyRow[] }) {
  return (
    <section className="mt-4 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-xs uppercase text-[var(--muted)]">Loop participants</div>
          <h3 className="mt-1 text-lg font-semibold">Organization details</h3>
        </div>
        <div className="rounded-full border border-[var(--border)] px-3 py-1 text-xs text-[var(--muted)]">{rows.length} entities</div>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {rows.slice(0, 6).map((row, index) => (
          <article key={index} className="rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] p-3">
            <div className="text-sm font-semibold">{participantTitle(row)}</div>
            <div className="mt-1 text-xs text-[var(--muted)]">{text(row.bn ?? row.BN ?? row.business_number ?? row.registration_number ?? row.entity_id ?? "No identifier shown")}</div>
            <div className="mt-3 grid gap-2 text-xs">
              <DetailLine label="Role" value={entityRole(row)} />
              {(row.total_sent !== undefined || row.sent_amount !== undefined) && <DetailLine label="Total sent" value={money(row.total_sent ?? row.sent_amount)} />}
              {(row.total_received !== undefined || row.received_amount !== undefined) && <DetailLine label="Total received" value={money(row.total_received ?? row.received_amount)} />}
              {(row.max_govt_share_pct !== undefined || row.loop_max_govt_share_pct !== undefined) && <DetailLine label="Government funding share" value={percent(row.max_govt_share_pct ?? row.loop_max_govt_share_pct)} />}
              {(row.max_strict_overhead_pct !== undefined || row.loop_max_strict_overhead_pct !== undefined) && <DetailLine label="Overhead indicator" value={percent(row.max_strict_overhead_pct ?? row.loop_max_strict_overhead_pct)} />}
              {(row.review_score !== undefined || row.score !== undefined) && <DetailLine label="Review score" value={score(row.review_score ?? row.score)} />}
              {(row.city !== undefined || row.province !== undefined) && <DetailLine label="Location" value={[row.city, row.province].filter(Boolean).map(String).join(", ")} />}
              {(row.designation !== undefined || row.status !== undefined || row.filing_status !== undefined) && <DetailLine label="Notes" value={text(row.designation ?? row.status ?? row.filing_status)} />}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function participantTitle(row: AnyRow) {
  return text(row.organization_name ?? row.legal_name ?? row.account_name ?? row.name ?? row.charity ?? row.charity_name ?? row.bn ?? row.BN ?? row.business_number ?? "Unknown organization");
}

function entityRole(row: AnyRow) {
  const sendsTo = row.sends_to ?? row.target_name ?? row.to_name;
  const receivesFrom = row.receives_from ?? row.source_name ?? row.from_name;
  if (sendsTo && receivesFrom) return `Sends to ${text(sendsTo)} and receives from ${text(receivesFrom)}`;
  if (sendsTo) return `Sends to ${text(sendsTo)}`;
  if (receivesFrom) return `Receives from ${text(receivesFrom)}`;
  return text(row.participant_role ?? row.role ?? row.position_in_loop ?? "Participant in the circular path");
}

function percent(value: unknown) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "n/a";
  if (n >= 0 && n <= 1) return `${(n * 100).toFixed(1)}%`;
  if (n > 1 && n <= 100) return `${n.toFixed(1)}%`;
  return `${n.toFixed(2)} ratio indicator`;
}

function DetailLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2 rounded-md bg-[var(--surface)] px-2 py-1.5">
      <span className="shrink-0 text-[var(--muted)]">{label}:</span>
      <span className="min-w-0 break-words font-medium">{value}</span>
    </div>
  );
}

function QuickActions({ onAsk }: { onAsk: (text: string) => void }) {
  const actions = [
    { label: "Show organization details", prompt: "Show organization details", icon: Users },
    { label: "Why flagged?", prompt: "Why was this loop flagged?", icon: AlertCircle },
    { label: "Show network view", prompt: "Show network view", icon: GitBranch },
    { label: "Generate neutral memo", prompt: "Generate neutral memo", icon: FileText }
  ];
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {actions.map(({ label, prompt, icon: Icon }) => (
        <button key={label} onClick={() => onAsk(prompt)} className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-xs transition hover:bg-[var(--surface-strong)]">
          <Icon size={13} />
          {label}
        </button>
      ))}
    </div>
  );
}

function FollowupChips({ followups, onAsk }: { followups?: string[]; onAsk: (text: string) => void }) {
  const safe = followups ?? [];
  if (!safe.length) return null;
  return (
    <div className="mt-4 flex flex-wrap gap-2">
      {safe.map((followup) => (
        <button key={followup} onClick={() => onAsk(followup)} className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-xs text-[var(--foreground)] transition hover:bg-[var(--surface-strong)]">
          {followup}
        </button>
      ))}
    </div>
  );
}
