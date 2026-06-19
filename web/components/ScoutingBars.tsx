"use client";

import { useState } from "react";
import Link from "next/link";

import { PercentileBar } from "@/components/PercentileBar";
import { CATEGORY_LABEL, displayPercentile, percentileColor } from "@/lib/format";
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
    <div>
      <div className="flex items-center gap-3 mb-5">
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
          vs {pool.positionBucket} · {pool.minutes} min
          {!pool.qualified && " · below minutes threshold (no percentiles)"}
        </span>
      </div>

      {/* Composite scores */}
      <section className="mb-7">
        <h3 className="text-xs uppercase tracking-wide text-neutral-500 mb-2">Composite ratings</h3>
        <div className="grid grid-cols-2 gap-x-6 gap-y-1">
          {composites.map((c) => {
            const color = percentileColor(c.score);
            return (
              <Link
                key={c.key}
                href={`${base}&kind=composite&key=${c.key}`}
                className="flex items-center gap-3 rounded px-2 -mx-2 py-1 hover:bg-neutral-900"
              >
                <div className="w-36 shrink-0 text-sm text-neutral-300 truncate">{c.label}</div>
                <div className="relative flex-1 h-5 rounded bg-neutral-800/80 overflow-hidden">
                  {c.score != null && (
                    <div
                      className="h-full rounded"
                      style={{ width: `${Math.max(2, c.score)}%`, backgroundColor: color }}
                    />
                  )}
                </div>
                <div className="w-8 text-right text-sm font-semibold tabular-nums" style={{ color }}>
                  {c.score == null ? "—" : Math.round(c.score)}
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      {CATEGORY_ORDER.map((cat) => {
        const lines = byCat(cat);
        if (lines.length === 0) return null;
        return (
          <section key={cat} className="mb-6">
            <h3 className="text-xs uppercase tracking-wide text-neutral-500 mb-1">
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
  );
}
