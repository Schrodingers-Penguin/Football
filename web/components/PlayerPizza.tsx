"use client";

import { CATEGORY_COLOR } from "@/lib/format";
import { STAT_BY_KEY, type StatCategory } from "@/lib/stats";

// Curated, category-contiguous slices (3 per category) — the FBref-style pizza.
const PIZZA_KEYS = [
  "npxg_p90",
  "shots_p90",
  "touches_in_att_pen_area_p90",
  "xa_p90",
  "key_passes_p90",
  "progressive_passes_p90",
  "xt_p90",
  "successful_take_ons_p90",
  "progressive_carries_p90",
  "tackles_p90",
  "interceptions_p90",
  "aerials_won_pct",
];

export interface PizzaStat {
  key: string;
  percentile: number | null; // already display-corrected (high = good)
}

export function PlayerPizza({ stats, size = 320 }: { stats: PizzaStat[]; size?: number }) {
  const pctByKey = new Map(stats.map((s) => [s.key, s.percentile]));
  const items = PIZZA_KEYS.map((k) => {
    const def = STAT_BY_KEY.get(k);
    return {
      key: k,
      label: def?.label ?? k,
      pct: pctByKey.get(k) ?? null,
      color: CATEGORY_COLOR[(def?.category ?? "attacking") as StatCategory],
    };
  });

  const cx = size / 2;
  const cy = size / 2;
  const maxR = size / 2 - 46;
  const n = items.length;
  const pt = (r: number, a: number) => [cx + r * Math.sin(a), cy - r * Math.cos(a)];
  const slice = (r: number, a0: number, a1: number) => {
    const [x0, y0] = pt(r, a0);
    const [x1, y1] = pt(r, a1);
    return `M ${cx} ${cy} L ${x0.toFixed(1)} ${y0.toFixed(1)} A ${r} ${r} 0 0 1 ${x1.toFixed(1)} ${y1.toFixed(1)} Z`;
  };

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-[340px] mx-auto">
      {/* reference rings */}
      {[0.25, 0.5, 0.75, 1].map((f) => (
        <circle
          key={f}
          cx={cx}
          cy={cy}
          r={maxR * f}
          fill="none"
          stroke="#262626"
          strokeWidth={1}
        />
      ))}
      {items.map((it, i) => {
        const a0 = (i * 2 * Math.PI) / n;
        const a1 = ((i + 1) * 2 * Math.PI) / n;
        const am = (a0 + a1) / 2;
        const r = it.pct == null ? 0 : maxR * (it.pct / 100);
        const [lx, ly] = pt(maxR + 14, am);
        const anchor = Math.sin(am) > 0.3 ? "start" : Math.sin(am) < -0.3 ? "end" : "middle";
        return (
          <g key={it.key}>
            <path d={slice(maxR, a0, a1)} fill={it.color} fillOpacity={0.08} />
            {it.pct != null && (
              <path d={slice(r, a0, a1)} fill={it.color} fillOpacity={0.85} stroke="#0a0a0a" strokeWidth={1} />
            )}
            <text
              x={lx}
              y={ly}
              fontSize={8.5}
              fill="#9ca3af"
              textAnchor={anchor}
              dominantBaseline="middle"
            >
              {it.label.length > 16 ? it.label.slice(0, 15) + "…" : it.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
