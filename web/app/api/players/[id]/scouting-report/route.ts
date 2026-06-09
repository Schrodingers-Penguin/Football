import { NextResponse } from "next/server";
import { z } from "zod";

import { getScoutingReport } from "@/lib/queries";

export const dynamic = "force-dynamic";

const Query = z.object({
  competition: z.coerce.number().int().positive(),
  season: z.string().trim().min(1),
});

export async function GET(req: Request, { params }: { params: { id: string } }) {
  const playerId = Number(params.id);
  if (!Number.isInteger(playerId)) {
    return NextResponse.json({ error: "invalid player id" }, { status: 400 });
  }
  const url = new URL(req.url);
  const parsed = Query.safeParse(Object.fromEntries(url.searchParams));
  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 });
  }
  try {
    const report = await getScoutingReport(playerId, parsed.data.competition, parsed.data.season);
    if (!report) {
      return NextResponse.json({ error: "no data for that player/competition/season" }, { status: 404 });
    }
    return NextResponse.json(report);
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 500 });
  }
}
