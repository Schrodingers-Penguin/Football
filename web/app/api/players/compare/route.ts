import { NextResponse } from "next/server";
import { z } from "zod";

import { comparePlayers } from "@/lib/queries";

export const dynamic = "force-dynamic";

const Query = z.object({
  id1: z.coerce.number().int().positive(),
  id2: z.coerce.number().int().positive(),
  competition: z.coerce.number().int().positive(),
  season: z.string().trim().min(1),
});

export async function GET(req: Request) {
  const url = new URL(req.url);
  const parsed = Query.safeParse(Object.fromEntries(url.searchParams));
  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 });
  }
  const { id1, id2, competition, season } = parsed.data;
  try {
    const result = await comparePlayers(id1, id2, competition, season);
    return NextResponse.json(result);
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 500 });
  }
}
