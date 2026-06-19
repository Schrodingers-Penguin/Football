"use client";

import { useState } from "react";
import Link from "next/link";

import { PercentileBar } from "@/components/PercentileBar";
import { CATEGORY_COLOR, CATEGORY_LABEL, displayPercentile, percentileColor } from "@/lib/format";
import { COMPOSITES } from "@/lib/composites";
import { CATEGORY_ORDER, STAT_BY_KEY, type StatCategory } from "@/lib/stats";
import type { ScoutingReport } from "@/lib/queries";

export function ScoutingBars({ report }: { report: ScoutingReport }) {
  const [poolIdx, setPoolIdx] = useState(0);
  const pool = report.pools[poolIdx];
  if (!pool) return <p className="text-neutral-400">No data.</p>;

  const base = `/rankings?competition=${report.competitionId}&season=${encodeURIComponent(
    report.seasonLabel,
  )}&position=${pool.positionBucket}`;

  const pctByKey = new Map(pool.stats.map((s) => [s.key, s.percentile]));
  const composites = COMPOSITES.map((c) => {
    const vals = c.members
      .map((k) => displayPercentile(pctByKey.get(k) ?? null, STAT_BY_KEY.get(k)?.lowerIsBetter))
      .filter((v): v is number => v != null);
    const score = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
    return { ...c, score };
  });

  const byCat = (cat: StatCategory) =>
    pool.stats.filter((s) => STAT_BY_KEY.get(s.key)?.category === cat);

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        {report.pools.length > 1 && (
          <div className="flex gap-1 rounded-lg bg-neutral-900 p-1">
            {report.pools.map((p, i) => (
              <button
                key={p.positionBucket}
                onClick={() => setPoolIdx(i)}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${
                  i === poolIdx ? "bg-neutral-700 text-white" : "text-neutral-400 hover:text-white"
                }`}
              >
                {p.positionBucket}
              </button>
            ))}
          </div>
        )}
        <span className="text-sm text-neutral-500">
          Percentile rank vs {pool.positionBucket} · {pool.minutes} min
          {pool.belowThreshold && " · below threshold (ranked vs pool, excluded from it)"}
        </span>
      </div>

      {/* Composite ratings — the headline */}
      <section className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
        <h3 className="text-xs uppercase tracking-wider text-neutral-500 mb-3">Composite ratings</h3>
        <div className="grid sm:grid-cols-2 gap-x-8 gap-y-2.5">
          {composites.map((c) => {
            const color = percentileColor(c.score);
            return (
              <Link
                key={c.key}
                href={`${base}&kind=composite&key=${c.key}`}
                className="flex items-center gap-3 rounded-md px-2 -mx-2 py-1 hover:bg-white/[0.03]"
              >
                <div className="w-32 shrink-0 text-[13px] text-neutral-300 truncate">{c.label}</div>
                <div className="relative flex-1 h-2.5 rounded-full bg-neutral-800/70 overflow-hidden">
                  {c.score != null && (
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${Math.max(2, c.score)}%`, backgroundColor: color }}
                    />
                  )}
                </div>
                <div
                  className="w-7 text-right text-base font-bold tabular-nums font-[family-name:var(--font-geist-mono)]"
                  style={{ color }}
                >
                  {c.score == null ? "—" : Math.round(c.score)}
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      {/* Stat categories */}
      <div className="grid lg:grid-cols-2 gap-4">
        {CATEGORY_ORDER.map((cat) => {
          const lines = byCat(cat);
          if (lines.length === 0) return null;
          return (
            <section key={cat} className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
              <h3 className="flex items-center gap-2 text-xs uppercase tracking-wider text-neutral-400 mb-2">
                <span
                  className="inline-block w-2 h-2 rounded-full"
                  style={{ backgroundColor: CATEGORY_COLOR[cat] }}
                />
                {CATEGORY_LABEL[cat]}
              </h3>
              {lines.map((s) => {
                const def = STAT_BY_KEY.get(s.key)!;
                return (
                  <PercentileBar
                    key={s.key}
                    def={def}
                    value={s.value}
                    percentile={s.percentile}
                    href={`${base}&kind=stat&key=${s.key}`}
                  />
                );
              })}
            </section>
          );
        })}
      </div>
    </div>
  );
}
