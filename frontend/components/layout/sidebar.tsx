"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bot, FileText, GitBranch, LayoutDashboard, Menu, Network, Search, ShieldCheck, X } from "lucide-react";
import { useState } from "react";
import { motion } from "framer-motion";
import { ThemeToggle } from "./theme-toggle";

const items = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/loops", label: "Loop Explorer", icon: Search },
  { href: "/network", label: "Network", icon: Network },
  { href: "/chat", label: "Ask LoopLens", icon: Bot },
  { href: "/memo", label: "Memo", icon: FileText }
];

function NavContent({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <>
      <Link href="/" onClick={onNavigate} className="mb-8 flex items-center gap-3 rounded-xl px-2 py-3">
        <div className="grid h-11 w-11 place-items-center rounded-xl bg-[var(--surface-muted)] text-[var(--accent)] soft-ring">
          <GitBranch size={21} />
        </div>
        <div>
          <div className="text-lg font-bold tracking-normal">LoopLens</div>
          <div className="text-xs text-[var(--muted)]">AI review intelligence</div>
        </div>
      </Link>
      <nav className="space-y-2">
        {items.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              className={`group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                active ? "bg-[var(--accent)] text-[var(--accent-foreground)] shadow-sm" : "text-[var(--muted)] hover:bg-[var(--surface-muted)] hover:text-[var(--foreground)]"
              }`}
            >
              <Icon size={18} className="transition group-hover:scale-110" />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="mt-7">
        <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">Theme</div>
        <ThemeToggle />
      </div>
      <div className="mt-7 rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-3 text-xs leading-5 text-[var(--muted)]">
        <div className="mb-2 flex items-center gap-2 font-semibold text-[var(--foreground)]">
          <ShieldCheck size={15} />
          Responsible use
        </div>
        Circular funding patterns are review-priority indicators only, not findings of wrongdoing.
      </div>
    </>
  );
}

export function Sidebar() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <div className="sticky top-0 z-30 mb-4 flex items-center justify-between rounded-xl border border-[var(--border)] bg-[var(--surface-strong)] px-3 py-2 backdrop-blur md:hidden">
        <Link href="/" className="flex items-center gap-2 font-bold">
          <GitBranch size={18} />
          LoopLens
        </Link>
        <button type="button" onClick={() => setOpen(true)} className="rounded-md border border-[var(--border)] p-2 text-[var(--foreground)]">
          <Menu size={18} />
        </button>
      </div>
      <aside className="fixed left-0 top-0 z-20 hidden h-screen w-64 border-r border-[var(--border)] bg-[var(--surface-strong)] p-4 backdrop-blur-xl md:block">
        <NavContent />
      </aside>
      {open && (
        <motion.div className="fixed inset-0 z-50 md:hidden" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <button type="button" aria-label="Close navigation" className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
          <motion.aside
            initial={{ x: -280 }}
            animate={{ x: 0 }}
            transition={{ type: "spring", stiffness: 260, damping: 26 }}
            className="relative h-full w-72 border-r border-[var(--border)] bg-[var(--surface-strong)] p-4 shadow-2xl backdrop-blur-xl"
          >
            <button type="button" onClick={() => setOpen(false)} className="absolute right-4 top-4 rounded-md border border-[var(--border)] p-2">
              <X size={16} />
            </button>
            <NavContent onNavigate={() => setOpen(false)} />
          </motion.aside>
        </motion.div>
      )}
    </>
  );
}
