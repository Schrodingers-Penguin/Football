"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

/** Per-stat minimum filter, committed on Enter or blur (not per keystroke —
 *  each commit is a server round-trip). */
export function StatMinInput({ statKey, value }: { statKey: string; value?: string }) {
  const router = useRouter();
  const params = useSearchParams();
  const [text, setText] = useState(value ?? "");

  // re-sync when the URL changes underneath us (back button, column removed)
  useEffect(() => setText(value ?? ""), [value]);

  function commit() {
    const trimmed = text.trim();
    if (trimmed === (value ?? "")) return;
    const q = new URLSearchParams(params.toString());
    if (trimmed === "" || Number.isNaN(Number(trimmed))) q.delete(`min_${statKey}`);
    else q.set(`min_${statKey}`, trimmed);
    router.push(`/traits?${q.toString()}`);
  }

  return (
    <input
      value={text}
      onChange={(e) => setText(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") e.currentTarget.blur();
      }}
      placeholder="min"
      inputMode="decimal"
      className="w-14 bg-transparent border border-neutral-800 rounded px-1 py-0.5 text-right
                 text-xs text-neutral-300 placeholder:text-neutral-700
                 focus:border-neutral-600 focus:outline-none"
    />
  );
}
