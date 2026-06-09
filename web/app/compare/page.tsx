"use client";

import { useEffect, useState } from "react";

import { CompareRadar } from "@/components/CompareRadar";
import { PlayerSearch } from "@/components/PlayerSearch";
import type { ScoutingReport } from "@/lib/queries";

interface Competition {
  id: number;
  name: string;
  seasons: string[];
}
interface Picked {
  id: number;
  name: string;
}

export default function ComparePage() {
  const [comps, setComps] = useState<Competition[]>([]);
  const [competition, setCompetition] = useState<number | null>(null);
  const [season, setSeason] = useState<string>("");
  const [p1, setP1] = useState<Picked | null>(null);
  const [p2, setP2] = useState<Picked | null>(null);
  const [reports, setReports] = useState<(ScoutingReport | null)[] | null>(null);

  useEffect(() => {
    fetch("/api/competitions")
      .then((r) => r.json())
      .then((d: { competitions: Competition[] }) => {
        setComps(d.competitions);
        if (d.competitions[0]) {
          setCompetition(d.competitions[0].id);
          setSeason(d.competitions[0].seasons[0] ?? "");
        }
      });
  }, []);

  useEffect(() => {
    if (!p1 || !p2 || !competition || !season) return;
    fetch(`/api/players/compare?id1=${p1.id}&id2=${p2.id}&competition=${competition}&season=${season}`)
      .then((r) => r.json())
      .then((d: { players: (ScoutingReport | null)[] }) => setReports(d.players));
  }, [p1, p2, competition, season]);

  const activeComp = comps.find((c) => c.id === competition);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Compare players</h1>

      <div className="flex flex-wrap gap-3 items-center text-sm">
        <select
          value={competition ?? ""}
          onChange={(e) => setCompetition(Number(e.target.value))}
          className="rounded-md bg-neutral-900 border border-neutral-700 px-3 py-1.5"
        >
          {comps.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <select
          value={season}
          onChange={(e) => setSeason(e.target.value)}
          className="rounded-md bg-neutral-900 border border-neutral-700 px-3 py-1.5"
        >
          {activeComp?.seasons.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="text-xs text-blue-400 mb-1">Player 1 {p1 && `· ${p1.name}`}</div>
          <PlayerSearch onSelect={setP1} placeholder="Player 1…" />
        </div>
        <div>
          <div className="text-xs text-red-400 mb-1">Player 2 {p2 && `· ${p2.name}`}</div>
          <PlayerSearch onSelect={setP2} placeholder="Player 2…" />
        </div>
      </div>

      {reports && reports[0] && reports[1] ? (
        <CompareRadar a={reports[0]} b={reports[1]} />
      ) : (
        <p className="text-neutral-500 text-sm">
          Pick two players (with data in the selected competition &amp; season).
        </p>
      )}
    </div>
  );
}
