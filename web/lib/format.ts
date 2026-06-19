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

/** Red (low) → amber → green (high) by percentile, for bar fills and dots.
 *  3-stop RGB interpolation — punchier and less muddy than a raw HSL sweep. */
export function percentileColor(pct: number | null): string {
  if (pct == null) return "#3f3f46"; // neutral grey when unranked
  const p = Math.max(0, Math.min(100, pct)) / 100;
  const stops: [number, number, number][] = [
    [225, 65, 75], // red
    [232, 168, 56], // amber
    [64, 192, 110], // green
  ];
  const lerp = (a: number, b: number, t: number) => Math.round(a + (b - a) * t);
  const [c0, c1] = p < 0.5 ? [stops[0], stops[1]] : [stops[1], stops[2]];
  const t = p < 0.5 ? p / 0.5 : (p - 0.5) / 0.5;
  return `rgb(${lerp(c0[0], c1[0], t)}, ${lerp(c0[1], c1[1], t)}, ${lerp(c0[2], c1[2], t)})`;
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
