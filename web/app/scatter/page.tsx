"use client";

import { useEffect, useMemo, useState } from "react";

import { PlayerSearch } from "@/components/PlayerSearch";
import { ScatterPlot } from "@/components/ScatterPlot";
import { STAT_CATALOG } from "@/lib/stats";
import { COMPETITION_COLOR } from "@/lib/format";
import type { ScatterResult } from "@/lib/queries";

const COMP_NAME: Record<number, string> = {
  2: "Premier League",
  3: "Bundesliga",
  4: "La Liga",
  5: "Serie A",
  13: "Eredivisie",
  21: "Primeira",
  22: "Ligue 1",
};

export default function ScatterPage() {
  const [seasons, setSeasons] = useState<string[]>([]);
  const [season, setSeason] = useState("");
  const [xKey, setXKey] = useState("xt_p90");
  const [yKey, setYKey] = useState("npxg_p90");
  const [minMinutes, setMinMinutes] = useState(900);
  const [data, setData] = useState<ScatterResult | null>(null);
  const [highlight, setHighlight] = useState<{ id: number; name: string }[]>([]);

  useEffect(() => {
    fetch("/api/competitions")
      .then((r) => r.json())
      .then((d: { competitions: { seasons: string[] }[] }) => {
        const labels = Array.from(new Set(d.competitions.flatMap((c) => c.seasons)))
          .sort()
          .reverse();
        setSeasons(labels);
        setSeason(labels[0] ?? "");
      });
  }, []);

  useEffect(() => {
    if (!season) return;
    const u = `/api/scatter?season=${encodeURIComponent(season)}&x=${xKey}&y=${yKey}&minMinutes=${minMinutes}`;
    fetch(u)
      .then((r) => r.json())
      .then((d: ScatterResult) => setData(d.points ? d : null));
  }, [season, xKey, yKey, minMinutes]);

  const highlightSet = useMemo(() => new Set(highlight.map((h) => h.id)), [highlight]);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Scatter</h1>

      <div className="flex flex-wrap gap-3 items-center text-sm">
        <AxisSelect label="X" value={xKey} onChange={setXKey} />
        <AxisSelect label="Y" value={yKey} onChange={setYKey} />
        <select
          value={season}
          onChange={(e) => setSeason(e.target.value)}
          className="rounded-md bg-neutral-900 border border-neutral-700 px-2 py-1.5"
        >
          {seasons.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-1 text-neutral-400">
          min
          <input
            type="number"
            value={minMinutes}
            onChange={(e) => setMinMinutes(Number(e.target.value))}
            className="w-20 rounded-md bg-neutral-900 border border-neutral-700 px-2 py-1.5"
          />
        </label>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="w-64">
          <PlayerSearch
            placeholder="Highlight a player…"
            onSelect={(p) =>
              setHighlight((h) => (h.some((x) => x.id === p.id) ? h : [...h, p]))
            }
          />
        </div>
        {highlight.map((h) => (
          <button
            key={h.id}
            onClick={() => setHighlight((cur) => cur.filter((x) => x.id !== h.id))}
            className="rounded-full bg-neutral-800 px-2 py-0.5 text-xs hover:bg-neutral-700"
          >
            {h.name} ✕
          </button>
        ))}
      </div>

      {data ? (
        <>
          <ScatterPlot points={data.points} xLabel={data.x.label} yLabel={data.y.label} highlight={highlightSet} />
          <div className="flex flex-wrap gap-3 text-xs text-neutral-400">
            {Object.entries(COMP_NAME).map(([cid, name]) => (
              <span key={cid} className="flex items-center gap-1">
                <span
                  className="inline-block w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: COMPETITION_COLOR[Number(cid)] }}
                />
                {name}
              </span>
            ))}
            <span className="text-neutral-500">({data.points.length} players)</span>
          </div>
        </>
      ) : (
        <p className="text-neutral-500 text-sm">Loading…</p>
      )}
    </div>
  );
}

function AxisSelect({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex items-center gap-1 text-neutral-400">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md bg-neutral-900 border border-neutral-700 px-2 py-1.5 max-w-52"
      >
        {STAT_CATALOG.map((s) => (
          <option key={s.key} value={s.key}>
            {s.label}
          </option>
        ))}
      </select>
    </label>
  );
}
