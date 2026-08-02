"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

const PRESETS: { label: string; min?: number; max?: number }[] = [
  { label: "U21", max: 20 },
  { label: "U23", max: 22 },
  { label: "23–27", min: 23, max: 27 },
  { label: "28+", min: 28 },
];

/** Age range filter. Committed on Enter/blur; presets apply immediately. */
export function AgeFilter({ min, max }: { min?: string; max?: string }) {
  const router = useRouter();
  const params = useSearchParams();
  const [lo, setLo] = useState(min ?? "");
  const [hi, setHi] = useState(max ?? "");

  useEffect(() => setLo(min ?? ""), [min]);
  useEffect(() => setHi(max ?? ""), [max]);

  function push(nextMin: string, nextMax: string) {
    const q = new URLSearchParams(params.toString());
    for (const [key, val] of [
      ["minAge", nextMin],
      ["maxAge", nextMax],
    ] as const) {
      if (val === "" || Number.isNaN(Number(val))) q.delete(key);
      else q.set(key, val);
    }
    router.push(`/traits?${q.toString()}`);
  }

  const activePreset = (p: (typeof PRESETS)[number]) =>
    String(p.min ?? "") === (min ?? "") && String(p.max ?? "") === (max ?? "");

  const box =
    "w-12 bg-transparent border border-neutral-800 rounded px-1 py-0.5 text-right " +
    "text-xs text-neutral-300 placeholder:text-neutral-700 focus:border-neutral-600 focus:outline-none";

  return (
    <div className="flex flex-wrap items-center gap-1.5 text-xs">
      <span className="text-neutral-500">Age:</span>
      {PRESETS.map((p) => (
        <button
          key={p.label}
          onClick={() => push(String(p.min ?? ""), String(p.max ?? ""))}
          className={`rounded px-2 py-0.5 border ${
            activePreset(p)
              ? "border-neutral-400 bg-neutral-800 text-white"
              : "border-neutral-800 text-neutral-400 hover:border-neutral-600"
          }`}
        >
          {p.label}
        </button>
      ))}
      <input
        value={lo}
        onChange={(e) => setLo(e.target.value)}
        onBlur={() => push(lo, hi)}
        onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
        placeholder="min"
        inputMode="numeric"
        className={box}
      />
      <span className="text-neutral-700">–</span>
      <input
        value={hi}
        onChange={(e) => setHi(e.target.value)}
        onBlur={() => push(lo, hi)}
        onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
        placeholder="max"
        inputMode="numeric"
        className={box}
      />
      {(min || max) && (
        <button
          onClick={() => push("", "")}
          className="text-neutral-500 hover:text-neutral-300 underline"
        >
          clear
        </button>
      )}
    </div>
  );
}
