import { NextResponse } from "next/server";

import { getCompetitions } from "@/lib/queries";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const competitions = await getCompetitions();
    return NextResponse.json({ competitions });
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 500 });
  }
}
