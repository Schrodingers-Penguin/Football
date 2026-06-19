import { NextResponse } from "next/server";
import { z } from "zod";

import { getScatter } from "@/lib/queries";

export const dynamic = "force-dynamic";

const Q = z.object({
  season: z.string().trim().min(1),
  x: z.string().trim().min(1),
  y: z.string().trim().min(1),
  minMinutes: z.coerce.number().int().nonnegative().default(0),
});

export async function GET(req: Request) {
  const parsed = Q.safeParse(Object.fromEntries(new URL(req.url).searchParams));
  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 });
  }
  const { season, x, y, minMinutes } = parsed.data;
  try {
    const result = await getScatter(season, x, y, { minMinutes });
    if (!result) return NextResponse.json({ error: "unknown stat or no data" }, { status: 404 });
    return NextResponse.json(result);
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 500 });
  }
}
