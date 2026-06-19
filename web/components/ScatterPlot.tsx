"use client";

import {
  CartesianGrid,
  Label,
  LabelList,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { COMPETITION_COLOR } from "@/lib/format";
import type { ScatterPoint } from "@/lib/queries";

const COMP_NAME: Record<number, string> = {
  2: "Premier League",
  3: "Bundesliga",
  4: "La Liga",
  5: "Serie A",
  13: "Eredivisie",
  21: "Primeira",
  22: "Ligue 1",
};

interface TipProps {
  active?: boolean;
  payload?: { payload: ScatterPoint }[];
}

function Tip({ active, payload }: TipProps) {
  if (!active || !payload || !payload.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded bg-neutral-900 border border-neutral-700 px-2 py-1 text-xs">
      <div className="text-neutral-100">{p.name}</div>
      <div className="text-neutral-400">
        {COMP_NAME[p.competitionId] ?? ""} · {p.minutes} min
      </div>
      <div className="text-neutral-300 tabular-nums">
        {p.x?.toFixed(2)}, {p.y?.toFixed(2)}
      </div>
    </div>
  );
}

export function ScatterPlot({
  points,
  xLabel,
  yLabel,
  highlight,
}: {
  points: ScatterPoint[];
  xLabel: string;
  yLabel: string;
  highlight: Set<number>;
}) {
  const valid = points.filter((p) => p.x != null && p.y != null);
  const byComp = new Map<number, ScatterPoint[]>();
  for (const p of valid) {
    if (!byComp.has(p.competitionId)) byComp.set(p.competitionId, []);
    byComp.get(p.competitionId)!.push(p);
  }
  const highlighted = valid.filter((p) => highlight.has(p.playerId));

  return (
    <ResponsiveContainer width="100%" height={520}>
      <ScatterChart margin={{ top: 16, right: 24, bottom: 36, left: 12 }}>
        <CartesianGrid stroke="#262626" />
        <XAxis type="number" dataKey="x" name={xLabel} tick={{ fill: "#888", fontSize: 11 }}>
          <Label value={xLabel} position="bottom" fill="#999" fontSize={12} />
        </XAxis>
        <YAxis type="number" dataKey="y" name={yLabel} tick={{ fill: "#888", fontSize: 11 }}>
          <Label value={yLabel} angle={-90} position="left" fill="#999" fontSize={12} />
        </YAxis>
        <Tooltip content={<Tip />} cursor={{ strokeDasharray: "3 3" }} />
        {Array.from(byComp.entries()).map(([cid, pts]) => (
          <Scatter
            key={cid}
            name={COMP_NAME[cid] ?? String(cid)}
            data={pts}
            fill={COMPETITION_COLOR[cid] ?? "#888"}
            fillOpacity={0.45}
          />
        ))}
        {highlighted.length > 0 && (
          <Scatter name="Highlighted" data={highlighted} fill="#ffffff" shape="star">
            <LabelList dataKey="name" position="top" fill="#fff" fontSize={11} />
          </Scatter>
        )}
      </ScatterChart>
    </ResponsiveContainer>
  );
}
