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
    <div className="group flex items-center gap-3 py-[3px]">
      <div className="w-48 shrink-0 text-[13px] text-neutral-400 group-hover:text-neutral-200 truncate">
        {def.label}
      </div>
      <div className="w-12 shrink-0 text-right text-[13px] tabular-nums text-neutral-200 font-[family-name:var(--font-geist-mono)]">
        {formatStat(value, def.format)}
      </div>
      <div className="relative flex-1 h-[18px] rounded-[5px] bg-neutral-800/60 overflow-hidden ring-1 ring-inset ring-white/5">
        {shown != null && (
          <div
            className="h-full rounded-[5px] transition-[width] duration-300"
            style={{ width: `${Math.max(1.5, shown)}%`, backgroundColor: color }}
          />
        )}
      </div>
      <div
        className="w-8 shrink-0 text-right text-[13px] font-semibold tabular-nums font-[family-name:var(--font-geist-mono)]"
        style={{ color }}
      >
        {shown == null ? "—" : Math.round(shown)}
      </div>
    </div>
  );

  if (!href) return body;
  return (
    <Link href={href} className="block rounded-md hover:bg-white/[0.03] -mx-2 px-2">
      {body}
    </Link>
  );
}
