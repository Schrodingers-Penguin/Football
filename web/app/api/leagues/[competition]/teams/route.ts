import { NextResponse } from "next/server";
import { z } from "zod";

import { getTeamsForSeason } from "@/lib/queries";

export const dynamic = "force-dynamic";

const Query = z.object({ season: z.string().trim().min(1) });

export async function GET(req: Request, { params }: { params: { competition: string } }) {
  const competitionId = Number(params.competition);
  if (!Number.isInteger(competitionId)) {
    return NextResponse.json({ error: "invalid competition id" }, { status: 400 });
  }
  const parsed = Query.safeParse(Object.fromEntries(new URL(req.url).searchParams));
  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 });
  }
  try {
    const result = await getTeamsForSeason(competitionId, parsed.data.season);
    if (!result) {
      return NextResponse.json({ error: "no data for that competition/season" }, { status: 404 });
    }
    return NextResponse.json({ competitionId, seasonLabel: parsed.data.season, ...result });
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 500 });
  }
}
