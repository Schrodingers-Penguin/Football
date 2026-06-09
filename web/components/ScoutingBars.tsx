"use client";

import { useState } from "react";

import { PercentileBar } from "@/components/PercentileBar";
import { CATEGORY_LABEL } from "@/lib/format";
import { CATEGORY_ORDER, STAT_BY_KEY, type StatCategory } from "@/lib/stats";
import type { ScoutingReport } from "@/lib/queries";

export function ScoutingBars({ report }: { report: ScoutingReport }) {
  const [poolIdx, setPoolIdx] = useState(0);
  const pool = report.pools[poolIdx];
  if (!pool) return <p className="text-neutral-400">No data.</p>;

  const byCat = (cat: StatCategory) =>
    pool.stats.filter((s) => STAT_BY_KEY.get(s.key)?.category === cat);

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
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
              return <PercentileBar key={s.key} def={def} value={s.value} percentile={s.percentile} />;
            })}
          </section>
        );
      })}
    </div>
  );
}
