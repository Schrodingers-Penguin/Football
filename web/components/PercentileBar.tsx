import type { StatDef } from "@/lib/stats";
import { CATEGORY_COLOR, displayPercentile, formatStat } from "@/lib/format";

export function PercentileBar({
  def,
  value,
  percentile,
}: {
  def: StatDef;
  value: number | null;
  percentile: number | null;
}) {
  const shown = displayPercentile(percentile, def.lowerIsBetter);
  const color = CATEGORY_COLOR[def.category];
  return (
    <div className="flex items-center gap-3 py-1">
      <div className="w-52 shrink-0 text-sm text-neutral-300">{def.label}</div>
      <div className="w-14 shrink-0 text-right text-sm tabular-nums text-neutral-100">
        {formatStat(value, def.format)}
      </div>
      <div className="relative flex-1 h-5 rounded bg-neutral-800 overflow-hidden">
        {shown != null && (
          <div
            className="h-full rounded"
            style={{ width: `${Math.max(2, shown)}%`, backgroundColor: color }}
          />
        )}
      </div>
      <div className="w-9 shrink-0 text-right text-sm tabular-nums text-neutral-400">
        {shown == null ? "—" : Math.round(shown)}
      </div>
    </div>
  );
}
