"use client";

import { Bar, BarChart, CartesianGrid, Cell, ComposedChart, Line, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ReactElement } from "react";
import { Card } from "@/components/ui/card";
import type { AnyRow } from "@/lib/types";

const palette = ["#14b8a6", "#3b82f6", "#f59e0b", "#8b5cf6", "#10b981", "#64748b"];

function num(value: unknown) {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function bucket(values: number[], size: number, label: string) {
  const buckets = new Map<string, number>();
  values.forEach((value) => {
    const start = Math.floor(value / size) * size;
    const key = `${start}-${start + size}`;
    buckets.set(key, (buckets.get(key) ?? 0) + 1);
  });
  return Array.from(buckets, ([range, count]) => ({ [label]: range, count })).slice(0, 14);
}

export function DashboardCharts({ loops, labels }: { loops: AnyRow[]; labels: { review_label: string; count: number }[] }) {
  const topFlow = [...loops].sort((a, b) => num(b.circular_flow ?? b.total_flow) - num(a.circular_flow ?? a.total_flow)).slice(0, 10).map((row) => ({
    loop: String(row.loop_id ?? row.id),
    flow: num(row.circular_flow ?? row.total_flow)
  }));
  const scoreBuckets = bucket(loops.map((row) => num(row.review_score ?? row.score)), 10, "score");
  const participantBuckets = bucket(loops.map((row) => num(row.participant_count)), 2, "participants");
  const flowByLabel = Object.values(
    loops.reduce<Record<string, { label: string; flow: number; loops: number }>>((acc, row) => {
      const label = String(row.review_label ?? row.label ?? "Unscored");
      acc[label] ??= { label, flow: 0, loops: 0 };
      acc[label].flow += num(row.circular_flow ?? row.total_flow);
      acc[label].loops += 1;
      return acc;
    }, {})
  );
  const yearData = loops.slice(0, 500).map((row) => ({
    loop: String(row.loop_id ?? row.id),
    min: num(row.min_year),
    max: num(row.max_year)
  })).filter((row) => row.min > 0 || row.max > 0).slice(0, 30);

  return (
    <div className="grid gap-5 xl:grid-cols-2">
      <ChartCard title="Review Label Distribution">
        <PieChart>
          <Pie data={labels} dataKey="count" nameKey="review_label" innerRadius={58} outerRadius={94} paddingAngle={3}>
            {labels.map((_entry, index) => <Cell key={index} fill={palette[index % palette.length]} />)}
          </Pie>
          <Tooltip contentStyle={tooltipStyle} />
        </PieChart>
      </ChartCard>
      <ChartCard title="Top Loops By Circular Flow">
        <BarChart data={topFlow}>
          <CartesianGrid stroke="rgba(148,163,184,.16)" vertical={false} />
          <XAxis dataKey="loop" stroke="var(--muted)" tick={{ fontSize: 11 }} />
          <YAxis stroke="var(--muted)" tick={{ fontSize: 11 }} />
          <Tooltip contentStyle={tooltipStyle} />
          <Bar dataKey="flow" fill="#14b8a6" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ChartCard>
      <ChartCard title="Score Distribution">
        <BarChart data={scoreBuckets}>
          <CartesianGrid stroke="rgba(148,163,184,.16)" vertical={false} />
          <XAxis dataKey="score" stroke="var(--muted)" tick={{ fontSize: 11 }} />
          <YAxis stroke="var(--muted)" tick={{ fontSize: 11 }} />
          <Tooltip contentStyle={tooltipStyle} />
          <Bar dataKey="count" fill="#3b82f6" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ChartCard>
      <ChartCard title="Participant Count Distribution">
        <BarChart data={participantBuckets}>
          <CartesianGrid stroke="rgba(148,163,184,.16)" vertical={false} />
          <XAxis dataKey="participants" stroke="var(--muted)" tick={{ fontSize: 11 }} />
          <YAxis stroke="var(--muted)" tick={{ fontSize: 11 }} />
          <Tooltip contentStyle={tooltipStyle} />
          <Bar dataKey="count" fill="#f59e0b" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ChartCard>
      <ChartCard title="Circular Flow By Review Label">
        <BarChart data={flowByLabel}>
          <CartesianGrid stroke="rgba(148,163,184,.16)" vertical={false} />
          <XAxis dataKey="label" stroke="var(--muted)" tick={{ fontSize: 11 }} />
          <YAxis stroke="var(--muted)" tick={{ fontSize: 11 }} />
          <Tooltip contentStyle={tooltipStyle} />
          <Bar dataKey="flow" fill="#8b5cf6" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ChartCard>
      <ChartCard title="Loop Year Range">
        <ComposedChart data={yearData}>
          <CartesianGrid stroke="rgba(148,163,184,.16)" vertical={false} />
          <XAxis dataKey="loop" stroke="var(--muted)" tick={{ fontSize: 11 }} />
          <YAxis stroke="var(--muted)" tick={{ fontSize: 11 }} domain={["dataMin", "dataMax"]} />
          <Tooltip contentStyle={tooltipStyle} />
          <Line type="monotone" dataKey="min" stroke="#14b8a6" dot={false} />
          <Line type="monotone" dataKey="max" stroke="#f59e0b" dot={false} />
        </ComposedChart>
      </ChartCard>
    </div>
  );
}

function ChartCard({ title, children }: { title: string; children: ReactElement }) {
  return (
    <Card className="h-80">
      <h2 className="mb-4 text-lg font-semibold">{title}</h2>
      <ResponsiveContainer width="100%" height="82%">
        {children}
      </ResponsiveContainer>
    </Card>
  );
}

const tooltipStyle = {
  background: "var(--surface-strong)",
  border: "1px solid var(--border)",
  borderRadius: 10,
  color: "var(--foreground)"
};
