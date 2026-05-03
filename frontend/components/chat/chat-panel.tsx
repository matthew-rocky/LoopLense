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
      const returnedLoopId = firstLoopId(response.data);
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
  const oneLoop = response.data.length === 1 && firstLoopId(response.data);
  return (
    <>
      {!unsupported && oneLoop ? <LoopSummaryCard row={response.data[0]} /> : null}
      {!unsupported && oneLoop ? <QuickActions onAsk={onAsk} /> : null}
      {!unsupported && <ChartRenderer chart={response.chart} rows={response.data} />}
      {!unsupported && response.memo ? <MemoDocument memo={response.memo} /> : null}
      {!unsupported && <EvidenceCards rows={response.evidence} />}
      {!unsupported && response.data.length ? (
        <details className="mt-4 rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-4">
          <summary className="cursor-pointer text-sm font-semibold">View returned records</summary>
          <DataTable rows={response.data} title="Returned records" />
        </details>
      ) : null}
      {!unsupported && <VerificationCards verification={response.memo_verification ?? response.verification} />}
      <FollowupChips followups={response.suggested_followups} onAsk={onAsk} />
      {!unsupported && process.env.NODE_ENV !== "production" && (
        <details className="mt-4 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3 text-xs text-[var(--muted)]">
          <summary className="cursor-pointer font-semibold">Show raw response</summary>
          <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap">{JSON.stringify(response, null, 2)}</pre>
        </details>
      )}
    </>
  );
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

function QuickActions({ onAsk }: { onAsk: (text: string) => void }) {
  const actions = [
    { label: "Why flagged?", prompt: "Why was this loop flagged?", icon: AlertCircle },
    { label: "Show participants", prompt: "Show participants", icon: Users },
    { label: "Show network", prompt: "Show network", icon: GitBranch },
    { label: "Generate memo", prompt: "Generate a neutral memo for this loop.", icon: FileText }
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
