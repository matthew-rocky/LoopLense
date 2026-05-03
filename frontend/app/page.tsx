import Link from "next/link";
import { ArrowRight, GitBranch } from "lucide-react";
import { Card } from "@/components/ui/card";
import { PageShell } from "@/components/layout/page-shell";

export default function HomePage() {
  return (
    <PageShell className="grid min-h-[calc(100vh-3rem)] content-center gap-8">
      <section className="glass relative overflow-hidden rounded-2xl p-8 md:p-12">
        <div className="absolute right-10 top-10 hidden h-80 w-80 md:block">
          <div className="absolute left-28 top-4 h-16 w-16 rounded-full border border-[var(--border)] bg-[var(--surface-muted)]" />
          <div className="absolute left-4 top-32 h-20 w-20 rounded-full border border-[var(--border)] bg-[var(--surface-muted)]" />
          <div className="absolute bottom-6 right-8 h-24 w-24 rounded-full border border-[var(--border)] bg-[var(--surface-muted)]" />
          <div className="absolute left-16 top-24 h-px w-52 rotate-12 bg-[var(--accent)]/40" />
          <div className="absolute left-14 top-48 h-px w-60 -rotate-12 bg-[var(--accent-2)]/35" />
          <div className="absolute right-20 top-24 h-52 w-px rotate-12 bg-[var(--warning)]/30" />
        </div>
        <div className="max-w-3xl">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--surface-muted)] px-3 py-1 text-sm text-[var(--accent)]">
            <GitBranch size={15} />
            Evidence-grounded review workspace
          </div>
          <h1 className="text-5xl font-bold tracking-normal md:text-7xl">LoopLens</h1>
          <p className="mt-4 text-2xl font-semibold text-[var(--accent)]">AI Review of Circular Charity Funding</p>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-[var(--muted)]">
            LoopLens surfaces circular funding patterns for human review using loaded charity records, deterministic scoring,
            evidence-grounded chat, neutral memos, and claim verification. It does not allege wrongdoing.
          </p>
          <Link href="/dashboard" className="mt-8 inline-flex items-center gap-2 rounded-lg bg-[var(--accent)] px-5 py-3 font-semibold text-[var(--accent-foreground)] transition hover:-translate-y-0.5 hover:brightness-110">
            Enter dashboard
            <ArrowRight size={18} />
          </Link>
        </div>
      </section>
      <div className="grid gap-4 md:grid-cols-3">
        <Card><h2 className="font-semibold">Review priority</h2><p className="mt-2 text-sm leading-6 text-[var(--muted)]">Labels help triage patterns requiring human review.</p></Card>
        <Card><h2 className="font-semibold">Grounded answers</h2><p className="mt-2 text-sm leading-6 text-[var(--muted)]">Chat responses attach rows, methods, and verification details.</p></Card>
        <Card><h2 className="font-semibold">Neutral memos</h2><p className="mt-2 text-sm leading-6 text-[var(--muted)]">Memo language stays bounded to available records and disclaimers.</p></Card>
      </div>
    </PageShell>
  );
}
