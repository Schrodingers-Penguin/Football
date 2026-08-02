import Link from "next/link";

import { getCompositeRanking, getStatRanking, type RankingResult } from "@/lib/queries";
import { COMPETITION_COLOR, formatStat, percentileColor } from "@/lib/format";
import { STAT_BY_KEY } from "@/lib/stats";

export const dynamic = "force-dynamic";

const MIN_PRESETS = [0, 450, 900, 1350];
const POSITIONS = ["GK", "CB", "FB", "DM", "CM", "AM", "W", "CF"];
const TOP5 = [2, 3, 4, 5, 22];
const ALL_LEAGUES = [2, 3, 4, 5, 13, 21, 22];
const LEAGUES: { id: number; short: string }[] = [
  { id: 2, short: "PL" },
  { id: 4, short: "La Liga" },
  { id: 3, short: "Bundesliga" },
  { id: 5, short: "Serie A" },
  { id: 22, short: "Ligue 1" },
  { id: 13, short: "Eredivisie" },
  { id: 21, short: "Primeira" },
];

export default async function RankingsPage({
  searchParams,
}: {
  searchParams: {
    competition?: string;
    scope?: string;
    season?: string;
    kind?: string;
    key?: string;
    position?: string;
    minMinutes?: string;
  };
}) {
  const competition = searchParams.competition ? Number(searchParams.competition) : undefined;
  const scope = searchParams.scope === "all" ? "all" : searchParams.scope === "top5" ? "top5" : undefined;
  const season = searchParams.season ?? "";
  const kind = searchParams.kind === "composite" ? "composite" : "stat";
  const key = searchParams.key ?? "";
  const position = searchParams.position;
  const minMinutes = Number(searchParams.minMinutes ?? 600);

  if ((!competition && !scope) || !season || !key) {
    return <p className="text-neutral-400">Pick a stat from a player&apos;s scouting report.</p>;
  }

  const competitionIds = scope === "all" ? ALL_LEAGUES : scope === "top5" ? TOP5 : [competition!];
  const opts = { positionBucket: position, minMinutes, limit: 100 };
  const result: RankingResult | null =
    kind === "composite"
      ? await getCompositeRanking(competitionIds, season, key, opts)
      : await getStatRanking(competitionIds, season, key, opts);

  if (!result) return <p className="text-neutral-400">No ranking data.</p>;
  const def = STAT_BY_KEY.get(key);

  const tail = `&season=${encodeURIComponent(season)}&kind=${kind}&key=${key}${
    position ? `&position=${position}` : ""
  }&minMinutes=${minMinutes}`;
  const scopeQ = scope ? `scope=${scope}` : `competition=${competition}`;
  // base query (current league + stat + minutes) without a position, for the position toggle
  const posBase = `${scopeQ}&season=${encodeURIComponent(season)}&kind=${kind}&key=${key}&minMinutes=${minMinutes}`;
  const scopeActive = (s: string) =>
    s === "top5" ? scope === "top5" : s === "all" ? scope === "all" : !scope && competition === Number(s);

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">{result.label}</h1>
        <p className="text-neutral-400 text-sm">
          {season}
          {position ? ` · ${position}` : " · all positions"} · {kind === "composite" ? "composite score" : "by value"}
        </p>
      </header>

      {/* League scope toggle */}
      <div className="flex flex-wrap items-center gap-1.5 text-xs">
        <Link
          href={`/rankings?scope=top5${tail}`}
          className={`rounded px-2 py-0.5 border ${scopeActive("top5") ? "border-neutral-400 bg-neutral-800 text-white" : "border-neutral-800 hover:border-neutral-600"}`}
        >
          Top 5
        </Link>
        <Link
          href={`/rankings?scope=all${tail}`}
          className={`rounded px-2 py-0.5 border ${scopeActive("all") ? "border-neutral-400 bg-neutral-800 text-white" : "border-neutral-800 hover:border-neutral-600"}`}
        >
          All
        </Link>
        <span className="text-neutral-700">|</span>
        {LEAGUES.map((l) => (
          <Link
            key={l.id}
            href={`/rankings?competition=${l.id}${tail}`}
            className={`rounded px-2 py-0.5 border ${scopeActive(String(l.id)) ? "border-neutral-400 bg-neutral-800 text-white" : "border-neutral-800 hover:border-neutral-600"}`}
          >
            {l.short}
          </Link>
        ))}
      </div>

      {/* Position toggle */}
      <div className="flex flex-wrap items-center gap-1.5 text-xs">
        <span className="text-neutral-500">Position:</span>
        <Link
          href={`/rankings?${posBase}`}
          className={`rounded px-2 py-0.5 border ${!position ? "border-neutral-400 bg-neutral-800 text-white" : "border-neutral-800 hover:border-neutral-600"}`}
        >
          All
        </Link>
        {POSITIONS.map((p) => (
          <Link
            key={p}
            href={`/rankings?${posBase}&position=${p}`}
            className={`rounded px-2 py-0.5 border ${position === p ? "border-neutral-400 bg-neutral-800 text-white" : "border-neutral-800 hover:border-neutral-600"}`}
          >
            {p}
          </Link>
        ))}
      </div>

      <div className="flex items-center gap-2 text-xs text-neutral-500">
        <span>Min minutes:</span>
        {MIN_PRESETS.map((m) => {
          const scopeQ = scope ? `scope=${scope}` : `competition=${competition}`;
          return (
            <Link
              key={m}
              href={`/rankings?${scopeQ}&season=${encodeURIComponent(season)}&kind=${kind}&key=${key}${position ? `&position=${position}` : ""}&minMinutes=${m}`}
              className={`rounded px-2 py-0.5 border ${m === minMinutes ? "border-neutral-500 bg-neutral-800 text-white" : "border-neutral-800 hover:border-neutral-600"}`}
            >
              {m}
            </Link>
          );
        })}
      </div>

      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="text-neutral-500 text-left">
            <th className="font-normal py-1 w-8">#</th>
            <th className="font-normal py-1">Player</th>
            <th className="font-normal py-1 w-12">Pos</th>
            <th className="font-normal py-1 w-16 text-right">Min</th>
            <th className="font-normal py-1 w-20 text-right">{kind === "composite" ? "Score" : "Value"}</th>
            <th className="font-normal py-1 w-12 text-right">Pct</th>
          </tr>
        </thead>
        <tbody>
          {result.rows.map((r) => (
            // competition is part of the key: a mid-season transfer gives one
            // player two rows with the same bucket, and duplicate keys make
            // React strand a stale row when the ranking changes
            <tr
              key={`${r.playerId}-${r.competitionId}-${r.positionBucket}`}
              className="border-t border-neutral-900"
            >
              <td className="py-1 text-neutral-500 tabular-nums">{r.rank}</td>
              <td className="py-1">
                <span
                  className="inline-block w-2 h-2 rounded-full mr-2 align-middle"
                  style={{ backgroundColor: COMPETITION_COLOR[r.competitionId] ?? "#666" }}
                />
                <Link
                  href={`/players/${r.playerId}?competition=${r.competitionId}&season=${encodeURIComponent(season)}`}
                  className="text-neutral-100 hover:underline"
                >
                  {r.name}
                </Link>
              </td>
              <td className="py-1 text-neutral-500">{r.positionBucket}</td>
              <td className="py-1 text-right tabular-nums text-neutral-400">{r.minutes}</td>
              <td className="py-1 text-right tabular-nums text-neutral-100">
                {kind === "composite" ? r.value : formatStat(r.value, def?.format ?? "value")}
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
