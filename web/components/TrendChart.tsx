"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { COMPOSITES } from "@/lib/composites";
import type { TrendPoint } from "@/lib/queries";

const COLORS = ["#ef4444", "#3b82f6", "#22c55e", "#a855f7", "#f59e0b", "#06b6d4"];

export function TrendChart({ points }: { points: TrendPoint[] }) {
  const data = points.map((p) => ({
    season: p.seasonLabel,
    ...Object.fromEntries(COMPOSITES.map((c) => [c.label, p.composites[c.key]])),
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 10, right: 16, left: -12, bottom: 0 }}>
        <CartesianGrid stroke="#262626" />
        <XAxis dataKey="season" tick={{ fill: "#888", fontSize: 11 }} />
        <YAxis domain={[0, 100]} tick={{ fill: "#888", fontSize: 11 }} />
        <Tooltip
          contentStyle={{ background: "#171717", border: "1px solid #404040", fontSize: 12 }}
        />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        {COMPOSITES.map((c, i) => (
          <Line
            key={c.key}
            type="monotone"
            dataKey={c.label}
            stroke={COLORS[i % COLORS.length]}
            strokeWidth={2}
            dot={{ r: 3 }}
            connectNulls
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
