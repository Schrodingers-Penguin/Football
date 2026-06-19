import Link from "next/link";

import type { StatDef } from "@/lib/stats";
import { displayPercentile, formatStat, percentileColor } from "@/lib/format";

export function PercentileBar({
  def,
  value,
  percentile,
  href,
}: {
  def: StatDef;
  value: number | null;
  percentile: number | null;
  href?: string;
}) {
  const shown = displayPercentile(percentile, def.lowerIsBetter);
  const color = percentileColor(shown);

  const body = (
    <div className="group flex items-center gap-3 py-1">
      <div className="w-52 shrink-0 text-sm text-neutral-300 group-hover:text-white truncate">
        {def.label}
      </div>
      <div className="w-14 shrink-0 text-right text-sm tabular-nums text-neutral-100">
        {formatStat(value, def.format)}
      </div>
      <div className="relative flex-1 h-5 rounded bg-neutral-800/80 overflow-hidden">
        {shown != null && (
          <div
            className="h-full rounded transition-all"
            style={{ width: `${Math.max(2, shown)}%`, backgroundColor: color }}
          />
        )}
      </div>
      <div className="w-9 shrink-0 text-right text-sm font-medium tabular-nums" style={{ color }}>
        {shown == null ? "—" : Math.round(shown)}
      </div>
    </div>
  );

  if (!href) return body;
  return (
    <Link href={href} className="block rounded hover:bg-neutral-900 -mx-2 px-2">
      {body}
    </Link>
  );
}
