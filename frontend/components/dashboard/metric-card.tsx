"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";

export function MetricCard({ label, value, helper }: { label: string; value: string; helper: string }) {
  const numeric = Number(value.replace(/[$,]/g, ""));
  const [shown, setShown] = useState(Number.isFinite(numeric) ? 0 : null);
  useEffect(() => {
    if (!Number.isFinite(numeric)) return;
    const id = window.setInterval(() => {
      setShown((current) => {
        const next = Math.min(numeric, (current ?? 0) + Math.max(1, numeric / 28));
        if (next >= numeric) window.clearInterval(id);
        return next;
      });
    }, 18);
    return () => window.clearInterval(id);
  }, [numeric]);
  const display = shown === null ? value : value.includes("$") ? `$${Math.round(shown).toLocaleString()}` : Math.round(shown).toLocaleString();
  return (
    <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} whileHover={{ y: -3 }} transition={{ duration: 0.45 }}>
      <Card className="min-h-32">
        <div className="text-sm text-[var(--muted)]">{label}</div>
        <div className="mt-4 text-3xl font-bold text-[var(--foreground)]">{display}</div>
        <div className="mt-3 text-xs text-[var(--muted)]">{helper}</div>
      </Card>
    </motion.div>
  );
}
