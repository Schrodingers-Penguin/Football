import Link from "next/link";

import { ScoutingBars } from "@/components/ScoutingBars";
import { getPlayerSeasons, getScoutingReport } from "@/lib/queries";

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

  const report = await getScoutingReport(playerId, active.competitionId, active.seasonLabel);

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
    </div>
  );
}
