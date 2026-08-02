"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { CATEGORY_COLOR, CATEGORY_LABEL } from "@/lib/format";
import { CATEGORY_ORDER, STAT_CATALOG } from "@/lib/stats";

/** Browse the stat catalogue by category and toggle stats as table columns.
 *  Selection lives in the `stats` query param so the table stays a server render. */
export function StatPicker({ selected }: { selected: string[] }) {
  const router = useRouter();
  const params = useSearchParams();
  const [open, setOpen] = useState(selected.length === 0);

  const sel = new Set(selected);

  function toggle(key: string) {
    const next = new Set(sel);
    if (next.has(key)) next.delete(key);
    else next.add(key);

    const q = new URLSearchParams(params.toString());
    // keep catalogue order so columns don't jump around as you pick
    const ordered = STAT_CATALOG.filter((s) => next.has(s.key)).map((s) => s.key);
    if (ordered.length) q.set("stats", ordered.join(","));
    else q.delete("stats");
    // a per-stat minimum on a removed column would keep filtering invisibly
    if (!next.has(key)) q.delete(`min_${key}`);
    // sorting by a column that's gone falls back to the first remaining one
    if (q.get("sort") === key) {
      q.delete("sort");
      q.delete("dir");
    }
    router.push(`/traits?${q.toString()}`);
  }

  return (
    <div className="border border-neutral-800 rounded">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-neutral-300 hover:text-white"
      >
        <span className="text-neutral-500">{open ? "▾" : "▸"}</span>
        Stats
        <span className="text-neutral-500">
          {selected.length ? `${selected.length} selected` : "none selected"}
        </span>
      </button>

      {open && (
        <div className="px-3 pb-3 space-y-3">
          {CATEGORY_ORDER.map((cat) => (
            <div key={cat}>
              <div className="flex items-center gap-2 mb-1.5">
                <span
                  className="inline-block w-2 h-2 rounded-full"
                  style={{ backgroundColor: CATEGORY_COLOR[cat] }}
                />
                <span className="text-xs text-neutral-400">{CATEGORY_LABEL[cat]}</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {STAT_CATALOG.filter((s) => s.category === cat).map((s) => {
                  const on = sel.has(s.key);
                  return (
                    <button
                      key={s.key}
                      onClick={() => toggle(s.key)}
                      className={`rounded px-2 py-0.5 border text-xs ${
                        on
                          ? "border-neutral-400 bg-neutral-800 text-white"
                          : "border-neutral-800 text-neutral-400 hover:border-neutral-600"
                      }`}
                    >
                      {s.label}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
