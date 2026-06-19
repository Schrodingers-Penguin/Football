import Link from "next/link";

import { ScoutingBars } from "@/components/ScoutingBars";
import { TrendChart } from "@/components/TrendChart";
import { COMPETITION_COLOR } from "@/lib/format";
import {
  getPlayerSeasons,
  getPlayerTrend,
  getScoutingReport,
  getSimilarPlayers,
} from "@/lib/queries";

export const dynamic = "force-dynamic";

export default async function PlayerPage({
  params,
  searchParams,
}: {
  params: { id: string };
  searchParams: { competition?: string; season?: string };
}) {
  const playerId = Number(params.id);
  const seasons = await getPlayerSeasons(playerId);
  if (!seasons) {
    return <p className="text-neutral-400">No data for this player.</p>;
  }

  const active =
    seasons.options.find(
      (o) => String(o.competitionId) === searchParams.competition && o.seasonLabel === searchParams.season,
    ) ?? seasons.options[0];

  const [report, trend, similar] = await Promise.all([
    getScoutingReport(playerId, active.competitionId, active.seasonLabel),
    getPlayerTrend(playerId),
    getSimilarPlayers(playerId, active.competitionId, active.seasonLabel),
  ]);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-white/10 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-4xl font-bold tracking-tight">{seasons.name}</h1>
            {report?.pools[0] && (
              <span className="rounded-md bg-neutral-800 px-2 py-1 text-sm font-medium text-neutral-300">
                {report.pools[0].positionBucket}
              </span>
            )}
          </div>
          <p className="text-neutral-400 mt-1.5">
            {active.competitionName} · {active.seasonLabel}
            {report?.pools[0] && (
              <span className="text-neutral-500"> · {report.pools[0].minutes} min</span>
            )}
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {seasons.options.map((o) => {
            const isActive = o === active;
            return (
              <Link
                key={`${o.competitionId}-${o.seasonLabel}`}
                href={`/players/${playerId}?competition=${o.competitionId}&season=${o.seasonLabel}`}
                className={`rounded-md px-2.5 py-1 text-xs border transition-colors ${
                  isActive
                    ? "border-neutral-500 bg-neutral-800 text-white"
                    : "border-neutral-800 text-neutral-400 hover:border-neutral-600"
                }`}
              >
                {o.competitionName} {o.seasonLabel}
              </Link>
            );
          })}
        </div>
      </header>

      {report ? <ScoutingBars report={report} /> : <p className="text-neutral-400">No report.</p>}

      <div className="grid lg:grid-cols-2 gap-4">
        {trend.length >= 2 && (
          <section className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
            <h3 className="text-xs uppercase tracking-wider text-neutral-500 mb-3">
              Composite trend by season
            </h3>
            <TrendChart points={trend} />
          </section>
        )}
        {similar && similar.players.length > 0 && (
          <section className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
            <h3 className="text-xs uppercase tracking-wider text-neutral-500 mb-3">
              Similar players ({similar.positionBucket}, {active.seasonLabel})
            </h3>
            <ul className="space-y-1">
              {similar.players.map((s) => (
                <li key={s.playerId} className="flex items-center gap-2 text-sm">
                  <span
                    className="inline-block w-2 h-2 rounded-full"
                    style={{ backgroundColor: COMPETITION_COLOR[s.competitionId] ?? "#666" }}
                  />
                  <Link
                    href={`/players/${s.playerId}?competition=${s.competitionId}&season=${encodeURIComponent(active.seasonLabel)}`}
                    className="text-neutral-200 hover:underline flex-1"
                  >
                    {s.name}
                  </Link>
                  <span className="tabular-nums text-neutral-500">{s.similarity}</span>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </div>
  );
}
