"use client";

import {
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Legend,
} from "recharts";

import { displayPercentile } from "@/lib/format";
import { STAT_BY_KEY } from "@/lib/stats";
import type { ScoutingReport } from "@/lib/queries";

// Curated radar spokes spanning the four categories.
const RADAR_KEYS = [
  "npxg_p90",
  "xa_p90",
  "sca_p90",
  "xt_p90",
  "progressive_passes_p90",
  "successful_take_ons_p90",
  "tackles_p90",
  "aerials_won_pct",
];

function poolPct(report: ScoutingReport, key: string): number | null {
  const pool = report.pools[0];
  const line = pool?.stats.find((s) => s.key === key);
  if (!line) return null;
  return displayPercentile(line.percentile, STAT_BY_KEY.get(key)?.lowerIsBetter);
}

export function CompareRadar({ a, b }: { a: ScoutingReport; b: ScoutingReport }) {
  const data = RADAR_KEYS.map((key) => ({
    stat: STAT_BY_KEY.get(key)?.label ?? key,
    [a.player.name]: poolPct(a, key) ?? 0,
    [b.player.name]: poolPct(b, key) ?? 0,
  }));

  return (
    <ResponsiveContainer width="100%" height={420}>
      <RadarChart data={data} outerRadius="70%">
        <PolarGrid stroke="#333" />
        <PolarAngleAxis dataKey="stat" tick={{ fill: "#999", fontSize: 11 }} />
        <Radar name={a.player.name} dataKey={a.player.name} stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.35} />
        <Radar name={b.player.name} dataKey={b.player.name} stroke="#ef4444" fill="#ef4444" fillOpacity={0.35} />
        <Legend />
      </RadarChart>
    </ResponsiveContainer>
  );
}
