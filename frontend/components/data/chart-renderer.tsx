"use client";

import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { AnyRow } from "@/lib/types";

const colors = ["#14b8a6", "#3b82f6", "#f59e0b", "#8b5cf6", "#10b981", "#64748b"];

export function ChartRenderer({ chart, rows }: { chart?: AnyRow; rows?: AnyRow[] }) {
  const data = rows ?? [];
  if (!chart || data.length === 0) return null;
  const type = String(chart.type ?? "table");
  const x = String(chart.x ?? "");
  const y = String(chart.y ?? "");
  if (!x) return null;
  if ((type === "histogram" || type === "hist" || type === "distribution") && data.some((row) => row[x] !== undefined)) {
    const values = data.map((row) => Number(row[x])).filter(Number.isFinite);
    const max = Math.max(...values, 1);
    const size = Math.max(1, max / 12);
    const buckets = Array.from(
      values.reduce<Map<string, number>>((acc, value) => {
        const start = Math.floor(value / size) * size;
        const key = `${Math.round(start).toLocaleString()}-${Math.round(start + size).toLocaleString()}`;
        acc.set(key, (acc.get(key) ?? 0) + 1);
        return acc;
      }, new Map()),
      ([range, count]) => ({ range, count })
    );
    return (
      <div className="mt-4 h-64 rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-4">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={buckets}>
            <CartesianGrid stroke="rgba(148,163,184,.18)" vertical={false} />
            <XAxis dataKey="range" stroke="var(--muted)" tick={{ fontSize: 10 }} />
            <YAxis stroke="var(--muted)" tick={{ fontSize: 11 }} />
            <Tooltip contentStyle={{ background: "var(--surface-strong)", border: "1px solid var(--border)", borderRadius: 10, color: "var(--foreground)" }} />
            <Bar dataKey="count" fill="#14b8a6" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }
  if (!y || !data.some((row) => row[x] !== undefined && row[y] !== undefined)) return null;
  if (type === "bar") {
    return (
      <div className="mt-4 h-64 rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-4">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data.slice(0, 16)}>
            <CartesianGrid stroke="rgba(148,163,184,.18)" vertical={false} />
            <XAxis dataKey={x} stroke="var(--muted)" tick={{ fontSize: 11 }} />
            <YAxis stroke="var(--muted)" tick={{ fontSize: 11 }} />
            <Tooltip contentStyle={{ background: "var(--surface-strong)", border: "1px solid var(--border)", borderRadius: 10, color: "var(--foreground)" }} />
            <Bar dataKey={y} radius={[6, 6, 0, 0]}>
              {data.slice(0, 16).map((_entry, index) => <Cell key={index} fill={colors[index % colors.length]} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }
  if (type === "pie") {
    return (
      <div className="mt-4 h-64 rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-4">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey={y} nameKey={x} innerRadius={54} outerRadius={92} paddingAngle={3}>
              {data.map((_entry, index) => <Cell key={index} fill={colors[index % colors.length]} />)}
            </Pie>
            <Tooltip contentStyle={{ background: "var(--surface-strong)", border: "1px solid var(--border)", borderRadius: 10, color: "var(--foreground)" }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    );
  }
  return null;
}
