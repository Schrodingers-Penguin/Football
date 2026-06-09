import Link from "next/link";

import {
  getCompetitions,
  getLeagueTrends,
  getTeamsForSeason,
  type LeagueSeasonRow,
} from "@/lib/queries";
import { TEAM_STAT_CATALOG } from "@/lib/stats";

export const dynamic = "force-dynamic";

function fmt(v: number | null): string {
  if (v == null) return "—";
  return Number.isInteger(v) ? String(v) : v.toFixed(2);
}

export default async function LeaguePage({
  params,
  searchParams,
}: {
  params: { competition: string };
  searchParams: { season?: string };
}) {
  const competitionId = Number(params.competition);
  const [competitions, trends] = await Promise.all([
    getCompetitions(),
    getLeagueTrends(competitionId),
  ]);
  const comp = competitions.find((c) => c.id === competitionId);
  const seasonLabels = trends.map((t) => t.seasonLabel);
  const activeSeason = searchParams.season ?? seasonLabels[seasonLabels.length - 1];
  const teamsData = activeSeason ? await getTeamsForSeason(competitionId, activeSeason) : null;

  const statByKey = (row: LeagueSeasonRow, key: string) => row.stats.find((s) => s.key === key);

  return (
    <div className="space-y-10">
      <header>
        <h1 className="text-2xl font-semibold">{comp?.name ?? "League"}</h1>
        <p className="text-neutral-400 text-sm">{comp?.country}</p>
      </header>

      {/* League totals by season (metric rows x season columns) */}
      <section>
        <h2 className="text-sm uppercase tracking-wide text-neutral-500 mb-3">
          League totals by season
        </h2>
        <div className="overflow-x-auto">
          <table className="text-sm border-collapse">
            <thead>
              <tr className="text-neutral-500">
                <th className="text-left font-normal py-1 pr-4">Metric</th>
                {trends.map((t) => (
                  <th key={t.seasonLabel} className="text-right font-normal py-1 px-3">
                    {t.seasonLabel}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {TEAM_STAT_CATALOG.map((def) => (
                <tr key={def.key} className="border-t border-neutral-900">
                  <td className="py-1 pr-4 text-neutral-300">{def.label}</td>
                  {trends.map((t) => (
                    <td key={t.seasonLabel} className="py-1 px-3 text-right tabular-nums">
                      {fmt(statByKey(t, def.key)?.total ?? null)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Per-team for a chosen season */}
      <section>
        <div className="flex items-center gap-3 mb-3">
          <h2 className="text-sm uppercase tracking-wide text-neutral-500">By team</h2>
          <div className="flex gap-1">
            {seasonLabels.map((s) => (
              <Link
                key={s}
                href={`/leagues/${competitionId}?season=${s}`}
                className={`rounded px-2 py-0.5 text-xs border ${
                  s === activeSeason
                    ? "border-neutral-500 bg-neutral-800 text-white"
                    : "border-neutral-800 text-neutral-400 hover:border-neutral-600"
                }`}
              >
                {s}
              </Link>
            ))}
          </div>
        </div>
        {teamsData && (
          <div className="overflow-x-auto">
            <table className="text-sm border-collapse whitespace-nowrap">
              <thead>
                <tr className="text-neutral-500">
                  <th className="text-left font-normal py-1 pr-4 sticky left-0 bg-[#0a0a0a]">Team</th>
                  {TEAM_STAT_CATALOG.map((def) => (
                    <th key={def.key} className="text-right font-normal py-1 px-3">
                      {def.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {teamsData.teams.map((t) => (
                  <tr key={t.teamId} className="border-t border-neutral-900">
                    <td className="py-1 pr-4 text-neutral-200 sticky left-0 bg-[#0a0a0a]">{t.name}</td>
                    {TEAM_STAT_CATALOG.map((def) => (
                      <td key={def.key} className="py-1 px-3 text-right tabular-nums text-neutral-300">
                        {fmt(t.stats.find((s) => s.key === def.key)?.total ?? null)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
