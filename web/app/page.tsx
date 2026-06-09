import Link from "next/link";

import { PlayerSearch } from "@/components/PlayerSearch";
import { getCompetitions } from "@/lib/queries";

export const dynamic = "force-dynamic";

export default async function Home() {
  const competitions = await getCompetitions();
  return (
    <div className="space-y-10">
      <section>
        <h1 className="text-2xl font-semibold mb-1">Player scouting</h1>
        <p className="text-neutral-400 text-sm mb-4">
          Search any player to see their percentile scouting report.
        </p>
        <PlayerSearch />
      </section>

      <section>
        <h2 className="text-sm uppercase tracking-wide text-neutral-500 mb-3">Leagues</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {competitions.map((c) => (
            <Link
              key={c.id}
              href={`/leagues/${c.id}`}
              className="rounded-lg border border-neutral-800 px-4 py-3 text-sm hover:border-neutral-600 hover:bg-neutral-900 transition-colors"
            >
              <div className="text-neutral-100">{c.name}</div>
              <div className="text-neutral-500 text-xs">{c.country}</div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
