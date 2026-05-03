"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export function LabelChart({ data }: { data: { review_label: string; count: number }[] }) {
  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid stroke="rgba(148,163,184,.16)" vertical={false} />
          <XAxis dataKey="review_label" stroke="#94a3b8" />
          <YAxis stroke="#94a3b8" allowDecimals={false} />
          <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid rgba(255,255,255,.12)", borderRadius: 8 }} />
          <Bar dataKey="count" fill="#2dd4bf" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

