import { NextResponse } from "next/server";

import { getLeagueTrends } from "@/lib/queries";

export const dynamic = "force-dynamic";

export async function GET(_req: Request, { params }: { params: { competition: string } }) {
  const competitionId = Number(params.competition);
  if (!Number.isInteger(competitionId)) {
    return NextResponse.json({ error: "invalid competition id" }, { status: 400 });
  }
  try {
    const seasons = await getLeagueTrends(competitionId);
    return NextResponse.json({ competitionId, seasons });
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 500 });
  }
}
