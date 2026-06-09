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
      <header>
        <h1 className="text-3xl font-bold">{seasons.name}</h1>
        <p className="text-neutral-400">
          {active.competitionName} · {active.seasonLabel}
        </p>
      </header>

      <div className="flex flex-wrap gap-2">
        {seasons.options.map((o) => {
          const isActive = o === active;
          return (
            <Link
              key={`${o.competitionId}-${o.seasonLabel}`}
              href={`/players/${playerId}?competition=${o.competitionId}&season=${o.seasonLabel}`}
              className={`rounded-md px-3 py-1 text-xs border transition-colors ${
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

      {report ? <ScoutingBars report={report} /> : <p className="text-neutral-400">No report.</p>}
    </div>
  );
}
