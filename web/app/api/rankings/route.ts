import { NextResponse } from "next/server";
import { z } from "zod";

import { getCompositeRanking, getStatRanking } from "@/lib/queries";

export const dynamic = "force-dynamic";

const TOP5 = [2, 3, 4, 5, 22]; // PL, Bundesliga, La Liga, Serie A, Ligue 1
const ALL_LEAGUES = [2, 3, 4, 5, 13, 21, 22];

const Q = z.object({
  competition: z.coerce.number().int().positive().optional(),
  scope: z.enum(["top5", "all"]).optional(),
  season: z.string().trim().min(1),
  kind: z.enum(["stat", "composite"]).default("stat"),
  key: z.string().trim().min(1),
  position: z.string().trim().min(1).optional(),
  minMinutes: z.coerce.number().int().nonnegative().default(0),
  limit: z.coerce.number().int().positive().max(500).default(100),
});

export async function GET(req: Request) {
  const parsed = Q.safeParse(Object.fromEntries(new URL(req.url).searchParams));
  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 });
  }
  const { competition, scope, season, kind, key, position, minMinutes, limit } = parsed.data;
  const competitionIds =
    scope === "all" ? ALL_LEAGUES : scope === "top5" ? TOP5 : competition ? [competition] : null;
  if (!competitionIds) {
    return NextResponse.json({ error: "competition or scope required" }, { status: 400 });
  }
  const opts = { positionBucket: position, minMinutes, limit };
  try {
    const result =
      kind === "composite"
        ? await getCompositeRanking(competitionIds, season, key, opts)
        : await getStatRanking(competitionIds, season, key, opts);
    if (!result) return NextResponse.json({ error: "unknown key or no data" }, { status: 404 });
    return NextResponse.json(result);
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 500 });
  }
}
