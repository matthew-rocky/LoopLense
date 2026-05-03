"use client";

import { useState } from "react";
import type { ComponentType } from "react";
import { AlertCircle, Bot, Loader2, Send, Sparkles, User } from "lucide-react";
import { motion } from "framer-motion";
import { postChat } from "@/lib/api";
import type { AnyRow, ChatResponse } from "@/lib/types";
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

  async function ask(text: string) {
    const prompt = text.trim();
    if (!prompt || loading) return;
    const userMessage: Message = { id: crypto.randomUUID(), role: "user", content: prompt };
    setMessages((current) => [...current, userMessage]);
    setLoading(true);
    setMessage("");
    try {
      const response = await postChat(prompt, selectedLoopId);
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
            {selectedLoopId && <div className="mt-1 text-xs text-[var(--muted)]">Selected loop context: {selectedLoopId}</div>}
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
            <MessageBubble key={item.id} message={item} />
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

function MessageBubble({ message }: { message: Message }) {
  const assistant = message.role === "assistant";
  return (
    <motion.article initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className={`flex gap-3 ${assistant ? "justify-start" : "justify-end"}`}>
      {assistant && <Avatar icon={message.error ? AlertCircle : Bot} />}
      <div className={`max-w-[min(920px,92%)] rounded-2xl border border-[var(--border)] p-4 ${assistant ? "bg-[var(--surface-muted)]" : "bg-[var(--accent)] text-[var(--accent-foreground)]"}`}>
        <p className="whitespace-pre-wrap leading-7">{message.content}</p>
        {message.response && <AssistantResponse response={message.response} />}
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

function AssistantResponse({ response }: { response: ChatResponse & { memo?: AnyRow; memo_verification?: AnyRow } }) {
  return (
    <>
      <ChartRenderer chart={response.chart} rows={response.data} />
      {response.memo ? <MemoDocument memo={response.memo} /> : null}
      <EvidenceCards rows={response.evidence} />
      <DataTable rows={response.data} title="Data returned" />
      <VerificationCards verification={response.memo_verification ?? response.verification} />
      {process.env.NODE_ENV !== "production" && (
        <details className="mt-4 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3 text-xs text-[var(--muted)]">
          <summary className="cursor-pointer font-semibold">Show raw response</summary>
          <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap">{JSON.stringify(response, null, 2)}</pre>
        </details>
      )}
    </>
  );
}
