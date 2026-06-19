import Link from "next/link";

import { getCompositeRanking, getStatRanking, type RankingResult } from "@/lib/queries";
import { formatStat, percentileColor } from "@/lib/format";
import { STAT_BY_KEY } from "@/lib/stats";

export const dynamic = "force-dynamic";

const MIN_PRESETS = [0, 450, 900, 1350];

export default async function RankingsPage({
  searchParams,
}: {
  searchParams: {
    competition?: string;
    season?: string;
    kind?: string;
    key?: string;
    position?: string;
    minMinutes?: string;
  };
}) {
  const competition = Number(searchParams.competition);
  const season = searchParams.season ?? "";
  const kind = searchParams.kind === "composite" ? "composite" : "stat";
  const key = searchParams.key ?? "";
  const position = searchParams.position;
  const minMinutes = Number(searchParams.minMinutes ?? 600);

  if (!competition || !season || !key) {
    return <p className="text-neutral-400">Pick a stat from a player&apos;s scouting report.</p>;
  }

  const opts = { positionBucket: position, minMinutes, limit: 100 };
  const result: RankingResult | null =
    kind === "composite"
      ? await getCompositeRanking(competition, season, key, opts)
      : await getStatRanking(competition, season, key, opts);

  if (!result) return <p className="text-neutral-400">No ranking data.</p>;

  const def = STAT_BY_KEY.get(key);
  const baseQ = `competition=${competition}&season=${encodeURIComponent(season)}&kind=${kind}&key=${key}${
    position ? `&position=${position}` : ""
  }`;

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">{result.label}</h1>
        <p className="text-neutral-400 text-sm">
          {season}
          {position ? ` · ${position}` : " · all positions"} · ranked by{" "}
          {kind === "composite" ? "composite score" : "value"}
        </p>
      </header>

      <div className="flex items-center gap-2 text-xs text-neutral-500">
        <span>Min minutes:</span>
        {MIN_PRESETS.map((m) => (
          <Link
            key={m}
            href={`/rankings?${baseQ}&minMinutes=${m}`}
            className={`rounded px-2 py-0.5 border ${
              m === minMinutes
                ? "border-neutral-500 bg-neutral-800 text-white"
                : "border-neutral-800 hover:border-neutral-600"
            }`}
          >
            {m}
          </Link>
        ))}
      </div>

      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="text-neutral-500 text-left">
            <th className="font-normal py-1 w-8">#</th>
            <th className="font-normal py-1">Player</th>
            <th className="font-normal py-1 w-12">Pos</th>
            <th className="font-normal py-1 w-16 text-right">Min</th>
            <th className="font-normal py-1 w-20 text-right">
              {kind === "composite" ? "Score" : "Value"}
            </th>
            <th className="font-normal py-1 w-12 text-right">Pct</th>
          </tr>
        </thead>
        <tbody>
          {result.rows.map((r) => (
            <tr key={`${r.playerId}-${r.positionBucket}`} className="border-t border-neutral-900">
              <td className="py-1 text-neutral-500 tabular-nums">{r.rank}</td>
              <td className="py-1">
                <Link
                  href={`/players/${r.playerId}?competition=${competition}&season=${encodeURIComponent(season)}`}
                  className="text-neutral-100 hover:underline"
                >
                  {r.name}
                </Link>
              </td>
              <td className="py-1 text-neutral-500">{r.positionBucket}</td>
              <td className="py-1 text-right tabular-nums text-neutral-400">{r.minutes}</td>
              <td className="py-1 text-right tabular-nums text-neutral-100">
                {kind === "composite"
                  ? r.value
                  : formatStat(r.value, def?.format ?? "value")}
              </td>
              <td
                className="py-1 text-right tabular-nums font-medium"
                style={{ color: percentileColor(r.percentile) }}
              >
                {r.percentile == null ? "—" : Math.round(r.percentile)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
