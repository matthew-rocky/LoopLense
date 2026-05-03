import { ChatPanel } from "@/components/chat/chat-panel";
import { PageShell } from "@/components/layout/page-shell";

export default async function ChatPage({ searchParams }: { searchParams: Promise<{ loop?: string }> }) {
  const params = await searchParams;
  return (
    <PageShell className="h-[calc(100vh-2rem)]">
      <header>
        <p className="text-sm font-semibold uppercase tracking-wide text-[var(--accent)]">Ask LoopLens</p>
        <h1 className="mt-2 text-4xl font-bold">Evidence-Grounded Chat</h1>
        <p className="mt-3 max-w-3xl text-[var(--muted)]">Answers are based on loaded records, selected loop context, and deterministic handlers for common review questions.</p>
      </header>
      <ChatPanel selectedLoopId={params.loop} />
    </PageShell>
  );
}
