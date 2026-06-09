/**
 * Server-side data access (Supabase service role). Import only in API routes /
 * server components — never in a 'use client' file.
 */
import { getSupabaseClient } from "@/lib/supabase";
import { STAT_CATALOG } from "@/lib/stats";

type Row = Record<string, unknown>;

function num(v: unknown): number | null {
  return typeof v === "number" ? v : null;
}

export interface PlayerSearchResult {
  id: number;
  name: string;
}

export interface StatLine {
  key: string;
  value: number | null;
  percentile: number | null;
}

export interface ScoutingPool {
  positionBucket: string;
  minutes: number;
  positionMinutes: number | null;
  qualified: boolean; // met the minutes threshold => has percentile ranks
  stats: StatLine[];
}

export interface ScoutingReport {
  player: { id: number; name: string };
  competitionId: number;
  seasonLabel: string;
  seasonId: number;
  pools: ScoutingPool[];
}

export async function searchPlayers(q: string, limit = 20): Promise<PlayerSearchResult[]> {
  const client = getSupabaseClient();
  const { data, error } = await client
    .from("players")
    .select("id,name")
    .ilike("name", `%${q}%`)
    .order("name")
    .limit(limit);
  if (error) throw error;
  return (data ?? []).map((r) => ({ id: r.id as number, name: r.name as string }));
}

async function resolveSeasonId(competitionId: number, seasonLabel: string): Promise<number | null> {
  const client = getSupabaseClient();
  const { data, error } = await client
    .from("seasons")
    .select("id")
    .eq("competition_id", competitionId)
    .eq("season_label", seasonLabel)
    .maybeSingle();
  if (error) throw error;
  return data ? (data.id as number) : null;
}

export async function getScoutingReport(
  playerId: number,
  competitionId: number,
  seasonLabel: string,
): Promise<ScoutingReport | null> {
  const client = getSupabaseClient();
  const seasonId = await resolveSeasonId(competitionId, seasonLabel);
  if (seasonId == null) return null;

  const [{ data: statRows, error: statErr }, { data: player, error: pErr }] = await Promise.all([
    client.from("player_season_stats").select("*").eq("season_id", seasonId).eq("player_id", playerId),
    client.from("players").select("id,name").eq("id", playerId).maybeSingle(),
  ]);
  if (statErr) throw statErr;
  if (pErr) throw pErr;
  if (!statRows || statRows.length === 0 || !player) return null;

  const { data: pctRows, error: pctErr } = await client
    .from("player_season_percentiles")
    .select("*")
    .eq("season_id", seasonId)
    .eq("player_id", playerId);
  if (pctErr) throw pctErr;
  const pctByBucket = new Map<string, Row>(
    (pctRows ?? []).map((r) => [r.position_bucket as string, r as Row]),
  );

  const pools: ScoutingPool[] = (statRows as Row[])
    .map((sr) => {
      const pct = pctByBucket.get(sr.position_bucket as string);
      const stats: StatLine[] = STAT_CATALOG.map((s) => ({
        key: s.key,
        value: num(sr[s.key]),
        percentile: pct ? num(pct[`${s.key}_pct`]) : null,
      }));
      return {
        positionBucket: sr.position_bucket as string,
        minutes: sr.minutes as number,
        positionMinutes: num(sr.position_minutes),
        qualified: pct != null,
        stats,
      };
    })
    .sort((a, b) => (b.positionMinutes ?? 0) - (a.positionMinutes ?? 0));

  return {
    player: { id: player.id as number, name: player.name as string },
    competitionId,
    seasonLabel,
    seasonId,
    pools,
  };
}

export async function comparePlayers(
  id1: number,
  id2: number,
  competitionId: number,
  seasonLabel: string,
): Promise<{ players: (ScoutingReport | null)[] }> {
  const [a, b] = await Promise.all([
    getScoutingReport(id1, competitionId, seasonLabel),
    getScoutingReport(id2, competitionId, seasonLabel),
  ]);
  return { players: [a, b] };
}
