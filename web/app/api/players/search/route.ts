import { NextResponse } from "next/server";
import { z } from "zod";

import { searchPlayers } from "@/lib/queries";

export const dynamic = "force-dynamic";

const Params = z.object({
  q: z.string().trim().min(1, "q is required"),
  limit: z.coerce.number().int().positive().max(50).default(20),
});

export async function GET(req: Request) {
  const url = new URL(req.url);
  const parsed = Params.safeParse(Object.fromEntries(url.searchParams));
  if (!parsed.success) {
    return NextResponse.json({ error: parsed.error.flatten() }, { status: 400 });
  }
  try {
    const players = await searchPlayers(parsed.data.q, parsed.data.limit);
    return NextResponse.json({ players });
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 500 });
  }
}
