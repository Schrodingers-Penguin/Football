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

/** Red (low) → amber → green (high) by percentile, for bar fills and dots. */
export function percentileColor(pct: number | null): string {
  if (pct == null) return "#3f3f46"; // neutral grey when unranked
  const hue = (Math.max(0, Math.min(100, pct)) / 100) * 130; // 0=red, 130=green
  return `hsl(${hue}, 68%, 45%)`;
}

/** Distinct colours per competition for scatter plots (by competition id). */
export const COMPETITION_COLOR: Record<number, string> = {
  2: "#ef4444", // Premier League
  3: "#f59e0b", // Bundesliga
  4: "#eab308", // La Liga
  5: "#22c55e", // Serie A
  13: "#06b6d4", // Eredivisie
  21: "#3b82f6", // Primeira
  22: "#a855f7", // Ligue 1
};
