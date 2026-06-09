import type { StatCategory, StatFormat } from "@/lib/stats";

export const CATEGORY_COLOR: Record<StatCategory, string> = {
  attacking: "#ef4444",
  passing: "#3b82f6",
  possession: "#22c55e",
  defending: "#a855f7",
};

export const CATEGORY_LABEL: Record<StatCategory, string> = {
  attacking: "Attacking",
  passing: "Passing & Creation",
  possession: "Possession",
  defending: "Defending",
};

export function formatStat(value: number | null, format: StatFormat): string {
  if (value == null) return "—";
  if (format === "percent") return `${value.toFixed(1)}%`;
  return value.toFixed(2);
}

/** Stored percentiles are ascending; invert lower-is-better so a tall bar = good. */
export function displayPercentile(pct: number | null, lowerIsBetter?: boolean): number | null {
  if (pct == null) return null;
  return lowerIsBetter ? 100 - pct : pct;
}
