import Link from "next/link";

import { AgeFilter } from "@/components/AgeFilter";
import { StatMinInput } from "@/components/StatMinInput";
import { StatPicker } from "@/components/StatPicker";
import { COMPETITION_COLOR, formatStat, percentileColor } from "@/lib/format";
import { getCompetitions, getPlayerExplorer, type ExplorerResult } from "@/lib/queries";
import { STAT_BY_KEY } from "@/lib/stats";

export const dynamic = "force-dynamic";

const MIN_PRESETS = [0, 450, 900, 1350];
const POSITIONS = ["GK", "CB", "FB", "DM", "CM", "AM", "W", "CF"];
const TOP5 = [2, 3, 4, 5, 22];
const LEAGUE_SHORT: Record<number, string> = {
  2: "PL",
  3: "Bundesliga",
  4: "La Liga",
  5: "Serie A",
  13: "Eredivisie",
  21: "Primeira",
  22: "Ligue 1",
};
const DEFAULT_STATS = ["npxg_p90", "xa_p90", "progressive_passes_p90"];

type Params = Record<string, string | undefined>;

/** Rebuild the query string with `changes` applied (null removes a key). */
function withParams(sp: Params, changes: Record<string, string | null>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(sp)) if (v != null) q.set(k, v);
  for (const [k, v] of Object.entries(changes)) {
    if (v === null) q.delete(k);
    else q.set(k, v);
  }
  return q.toString();
}

const chip = (active: boolean) =>
  `rounded px-2 py-0.5 border ${
    active
      ? "border-neutral-400 bg-neutral-800 text-white"
      : "border-neutral-800 hover:border-neutral-600"
  }`;

export default async function TraitsPage({ searchParams }: { searchParams: Params }) {
  const competitions = await getCompetitions();
  const allLeagueIds = competitions.map((c) => c.id).filter((id) => id in LEAGUE_SHORT);
  const seasonLabels = Array.from(new Set(competitions.flatMap((c) => c.seasons)))
    .sort()
    .reverse();

  const scope = searchParams.scope === "all" ? "all" : searchParams.scope === "top5" ? "top5" : undefined;
  const competition = searchParams.competition ? Number(searchParams.competition) : undefined;
  // default to the Top 5 so the page is useful on first load
  const effectiveScope = scope ?? (competition ? undefined : "top5");
  const competitionIds =
    effectiveScope === "all" ? allLeagueIds : effectiveScope === "top5" ? TOP5 : [competition!];

  const season = searchParams.season ?? seasonLabels[0] ?? "";
  const position = searchParams.position;
  const minMinutes = Number(searchParams.minMinutes ?? 600);
  const statKeys = (searchParams.stats ?? DEFAULT_STATS.join(","))
    .split(",")
    .filter((k) => STAT_BY_KEY.has(k));

  const minValues: Record<string, number> = {};
  for (const k of statKeys) {
    const raw = searchParams[`min_${k}`];
    if (raw != null && raw !== "" && !Number.isNaN(Number(raw))) minValues[k] = Number(raw);
  }

  const numParam = (v: string | undefined) =>
    v != null && v !== "" && !Number.isNaN(Number(v)) ? Number(v) : undefined;
  const minAge = numParam(searchParams.minAge);
  const maxAge = numParam(searchParams.maxAge);

  const sortKey = searchParams.sort && STAT_BY_KEY.has(searchParams.sort) ? searchParams.sort : undefined;
  const sortDir = searchParams.dir === "asc" ? "asc" : searchParams.dir === "desc" ? "desc" : undefined;

  const result: ExplorerResult | null = statKeys.length
    ? await getPlayerExplorer(competitionIds, season, statKeys, {
        positionBucket: position,
        minMinutes,
        sortKey,
        sortDir,
        minValues,
        minAge,
        maxAge,
        limit: 100,
      })
    : null;

  const scopeActive = (s: string) =>
    s === "top5"
      ? effectiveScope === "top5"
      : s === "all"
        ? effectiveScope === "all"
        : !effectiveScope && competition === Number(s);

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold">Traits</h1>
        <p className="text-neutral-400 text-sm">
          Pick any stats as columns, then sort and filter the player pool.
        </p>
      </header>

      {/* League scope */}
      <div className="flex flex-wrap items-center gap-1.5 text-xs">
        <Link href={`/traits?${withParams(searchParams, { scope: "top5", competition: null })}`} className={chip(scopeActive("top5"))}>
          Top 5
        </Link>
        <Link href={`/traits?${withParams(searchParams, { scope: "all", competition: null })}`} className={chip(scopeActive("all"))}>
          All
        </Link>
        <span className="text-neutral-700">|</span>
        {allLeagueIds.map((id) => (
          <Link
            key={id}
            href={`/traits?${withParams(searchParams, { competition: String(id), scope: null })}`}
            className={chip(scopeActive(String(id)))}
          >
            {LEAGUE_SHORT[id]}
          </Link>
        ))}
      </div>

      {/* Season */}
      <div className="flex flex-wrap items-center gap-1.5 text-xs">
        <span className="text-neutral-500">Season:</span>
        {seasonLabels.map((s) => (
          <Link key={s} href={`/traits?${withParams(searchParams, { season: s })}`} className={chip(s === season)}>
            {s}
          </Link>
        ))}
      </div>

      {/* Position */}
      <div className="flex flex-wrap items-center gap-1.5 text-xs">
        <span className="text-neutral-500">Position:</span>
        <Link href={`/traits?${withParams(searchParams, { position: null })}`} className={chip(!position)}>
          All
        </Link>
        {POSITIONS.map((p) => (
          <Link key={p} href={`/traits?${withParams(searchParams, { position: p })}`} className={chip(position === p)}>
            {p}
          </Link>
        ))}
      </div>

      {/* Minutes */}
      <div className="flex flex-wrap items-center gap-1.5 text-xs">
        <span className="text-neutral-500">Min minutes:</span>
        {MIN_PRESETS.map((m) => (
          <Link
            key={m}
            href={`/traits?${withParams(searchParams, { minMinutes: String(m) })}`}
            className={chip(m === minMinutes)}
          >
            {m}
          </Link>
        ))}
      </div>

      <div className="space-y-1">
        <AgeFilter min={searchParams.minAge} max={searchParams.maxAge} />
        {result?.ageAsOf && (
          // WhoScored only reports age at scrape time, so this is a snapshot, not
          // a live age — say so rather than let a stale year pass as current
          <p className="text-[11px] text-neutral-600">Ages as of {result.ageAsOf}</p>
        )}
      </div>

      <StatPicker selected={statKeys} />

      {!statKeys.length ? (
        <p className="text-neutral-400 text-sm">Pick at least one stat to build the table.</p>
      ) : !result ? (
        <p className="text-neutral-400 text-sm">No data for this league and season.</p>
      ) : (
        <>
          <p className="text-xs text-neutral-500">
            {result.matched} players match
            {result.matched > result.rows.length ? ` — showing the top ${result.rows.length}` : ""}
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="text-neutral-500 text-left align-bottom">
                  <th className="font-normal py-1 w-8">#</th>
                  <th className="font-normal py-1 min-w-40">Player</th>
                  <th className="font-normal py-1 w-12">Pos</th>
                  <th className="font-normal py-1 w-12 text-right">Age</th>
                  <th className="font-normal py-1 w-16 text-right">Min</th>
                  {statKeys.map((k) => {
                    const def = STAT_BY_KEY.get(k)!;
                    // clicking the active column flips direction; a new column starts best-first
                    const activeSort = (sortKey ?? statKeys[0]) === k;
                    const currentDir = sortDir ?? (def.lowerIsBetter ? "asc" : "desc");
                    const nextDir = activeSort && currentDir === "desc" ? "asc" : "desc";
                    return (
                      <th key={k} className="font-normal py-1 px-2 text-right whitespace-nowrap">
                        <Link
                          href={`/traits?${withParams(searchParams, { sort: k, dir: nextDir })}`}
                          className={`hover:text-neutral-300 ${activeSort ? "text-neutral-200" : ""}`}
                        >
                          {def.label}
                          {activeSort ? (currentDir === "asc" ? " ↑" : " ↓") : ""}
                        </Link>
                        <div className="mt-1">
                          <StatMinInput statKey={k} value={searchParams[`min_${k}`]} />
                        </div>
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody>
                {result.rows.map((r, i) => (
                  <tr key={`${r.playerId}-${r.positionBucket}`} className="border-t border-neutral-900">
                    <td className="py-1 text-neutral-500 tabular-nums">{i + 1}</td>
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
                    <td className="py-1 text-right tabular-nums text-neutral-400">{r.age ?? "—"}</td>
                    <td className="py-1 text-right tabular-nums text-neutral-400">{r.minutes}</td>
                    {statKeys.map((k) => (
                      <td key={k} className="py-1 px-2 text-right tabular-nums whitespace-nowrap">
                        <span className="text-neutral-100">
                          {formatStat(r.values[k], STAT_BY_KEY.get(k)!.format)}
                        </span>
                        <span
                          className="ml-2 text-xs font-medium"
                          style={{ color: percentileColor(r.percentiles[k]) }}
                        >
                          {r.percentiles[k] == null ? "—" : Math.round(r.percentiles[k]!)}
                        </span>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
