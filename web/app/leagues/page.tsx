import Link from "next/link";

import { getCompetitions } from "@/lib/queries";

export const dynamic = "force-dynamic";

export default async function LeaguesPage() {
  const competitions = await getCompetitions();
  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Leagues</h1>
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
    </div>
  );
}
