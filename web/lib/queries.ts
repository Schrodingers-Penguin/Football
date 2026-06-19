/**
 * Server-side data access (Supabase service role). Import only in API routes /
 * server components — never in a 'use client' file.
 */
import { getSupabaseClient } from "@/lib/supabase";
import { COMPOSITE_BY_KEY } from "@/lib/composites";
import { STAT_BY_KEY, STAT_CATALOG, TEAM_STAT_CATALOG } from "@/lib/stats";

function dispPct(pct: number | null, lowerIsBetter?: boolean): number | null {
  if (pct == null) return null;
  return lowerIsBetter ? 100 - pct : pct;
}

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

export interface PlayerSeasonOption {
  competitionId: number;
  competitionName: string;
  seasonLabel: string;
  minutes: number;
}

/** The (competition, season) pools a player has data for, most minutes first. */
export async function getPlayerSeasons(playerId: number): Promise<{
  name: string;
  options: PlayerSeasonOption[];
} | null> {
  const client = getSupabaseClient();
  const [{ data: player }, { data: rows, error }] = await Promise.all([
    client.from("players").select("id,name").eq("id", playerId).maybeSingle(),
    client.from("player_season_stats").select("season_id,minutes").eq("player_id", playerId),
  ]);
  if (error) throw error;
  if (!player || !rows || rows.length === 0) return null;

  // collapse hybrid rows to one entry per season (max minutes across buckets)
  const minutesBySeason = new Map<number, number>();
  for (const r of rows) {
    const sid = r.season_id as number;
    minutesBySeason.set(sid, Math.max(minutesBySeason.get(sid) ?? 0, (r.minutes as number) ?? 0));
  }
  const { data: seasons } = await client
    .from("seasons")
    .select("id,competition_id,season_label")
    .in("id", Array.from(minutesBySeason.keys()));
  const { data: comps } = await client.from("competitions").select("id,name");
  const compName = new Map<number, string>((comps ?? []).map((c) => [c.id as number, c.name as string]));

  const options: PlayerSeasonOption[] = (seasons ?? []).map((s) => ({
    competitionId: s.competition_id as number,
    competitionName: compName.get(s.competition_id as number) ?? "",
    seasonLabel: s.season_label as string,
    minutes: minutesBySeason.get(s.id as number) ?? 0,
  }));
  options.sort((a, b) => b.minutes - a.minutes || b.seasonLabel.localeCompare(a.seasonLabel));
  return { name: player.name as string, options };
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

// ---------------------------------------------------------------------------
// Team / league aggregates
// ---------------------------------------------------------------------------

export interface CompetitionInfo {
  id: number;
  name: string;
  country: string;
  seasons: string[]; // labels, newest first
}

export interface AggStatLine {
  key: string;
  total: number | null;
  perMatch: number | null; // null for ratio metrics (already a %)
}

export interface LeagueSeasonRow {
  seasonLabel: string;
  matchesPlayed: number;
  stats: AggStatLine[];
}

export interface TeamRow {
  teamId: number;
  name: string;
  matchesPlayed: number;
  stats: AggStatLine[];
}

function aggLines(row: Row, matches: number): AggStatLine[] {
  return TEAM_STAT_CATALOG.map((s) => {
    const total = num(row[s.key]);
    return {
      key: s.key,
      total,
      perMatch: s.ratio || total == null || matches === 0 ? null : Number((total / matches).toFixed(3)),
    };
  });
}

export async function getCompetitions(): Promise<CompetitionInfo[]> {
  const client = getSupabaseClient();
  const [{ data: comps, error: cErr }, { data: seasons, error: sErr }] = await Promise.all([
    client.from("competitions").select("id,name,country").order("name"),
    client.from("seasons").select("competition_id,season_label"),
  ]);
  if (cErr) throw cErr;
  if (sErr) throw sErr;
  const byComp = new Map<number, string[]>();
  for (const s of seasons ?? []) {
    const cid = s.competition_id as number;
    if (!byComp.has(cid)) byComp.set(cid, []);
    byComp.get(cid)!.push(s.season_label as string);
  }
  return (comps ?? []).map((c) => ({
    id: c.id as number,
    name: c.name as string,
    country: c.country as string,
    seasons: (byComp.get(c.id as number) ?? []).sort().reverse(),
  }));
}

export async function getLeagueTrends(competitionId: number): Promise<LeagueSeasonRow[]> {
  const client = getSupabaseClient();
  const [{ data: rows, error }, { data: seasons }] = await Promise.all([
    client.from("league_season_stats").select("*").eq("competition_id", competitionId),
    client.from("seasons").select("id,season_label").eq("competition_id", competitionId),
  ]);
  if (error) throw error;
  const labelById = new Map<number, string>(
    (seasons ?? []).map((s) => [s.id as number, s.season_label as string]),
  );
  return (rows as Row[])
    .map((r) => {
      const matches = (r.matches_played as number) ?? 0;
      return {
        seasonLabel: labelById.get(r.season_id as number) ?? String(r.season_id),
        matchesPlayed: matches,
        stats: aggLines(r, matches),
      };
    })
    .sort((a, b) => a.seasonLabel.localeCompare(b.seasonLabel));
}

// ---------------------------------------------------------------------------
// Rankings (leaderboards) and scatter
// ---------------------------------------------------------------------------

export interface RankRow {
  rank: number;
  playerId: number;
  name: string;
  positionBucket: string;
  minutes: number;
  value: number | null;
  percentile: number | null;
}

export interface RankingResult {
  kind: "stat" | "composite";
  key: string;
  label: string;
  competitionId: number;
  seasonLabel: string;
  rows: RankRow[];
}

async function namesFor(client: ReturnType<typeof getSupabaseClient>, ids: number[]) {
  const { data } = await client.from("players").select("id,name").in("id", ids);
  return new Map<number, string>((data ?? []).map((p) => [p.id as number, p.name as string]));
}

/** Dedupe hybrid players to one row (per-90 values are identical across their
 *  buckets) — keep the bucket with the most minutes. */
function dedupePlayers(rows: Row[]): Row[] {
  const best = new Map<number, Row>();
  for (const r of rows) {
    const pid = r.player_id as number;
    const cur = best.get(pid);
    if (!cur || (r.minutes as number) > (cur.minutes as number)) best.set(pid, r);
  }
  return Array.from(best.values());
}

export async function getStatRanking(
  competitionId: number,
  seasonLabel: string,
  statKey: string,
  opts: { positionBucket?: string; minMinutes?: number; limit?: number } = {},
): Promise<RankingResult | null> {
  const def = STAT_BY_KEY.get(statKey);
  if (!def) return null;
  const client = getSupabaseClient();
  const seasonId = await resolveSeasonId(competitionId, seasonLabel);
  if (seasonId == null) return null;
  const minMinutes = opts.minMinutes ?? 0;

  let q = client
    .from("player_season_stats")
    .select(`player_id,position_bucket,minutes,${statKey}`)
    .eq("season_id", seasonId)
    .gte("minutes", minMinutes);
  if (opts.positionBucket) q = q.eq("position_bucket", opts.positionBucket);
  const { data, error } = await q;
  if (error) throw error;

  const pctCol = `${statKey}_pct`;
  const { data: pctRows } = await client
    .from("player_season_percentiles")
    .select(`player_id,position_bucket,${pctCol}`)
    .eq("season_id", seasonId);
  const pctMap = new Map<string, number | null>(
    ((pctRows ?? []) as unknown as Row[]).map((r) => [
      `${r.player_id}:${r.position_bucket}`,
      num(r[pctCol]),
    ]),
  );

  const rowsRaw = opts.positionBucket ? (data as unknown as Row[]) : dedupePlayers(data as unknown as Row[]);
  const names = await namesFor(client, rowsRaw.map((r) => r.player_id as number));

  const sign = def.lowerIsBetter ? 1 : -1;
  const sorted = rowsRaw
    .filter((r) => num(r[statKey]) != null)
    .sort((a, b) => sign * ((num(a[statKey]) ?? 0) - (num(b[statKey]) ?? 0)));

  const rows: RankRow[] = sorted.slice(0, opts.limit ?? 100).map((r, i) => ({
    rank: i + 1,
    playerId: r.player_id as number,
    name: names.get(r.player_id as number) ?? String(r.player_id),
    positionBucket: r.position_bucket as string,
    minutes: r.minutes as number,
    value: num(r[statKey]),
    percentile: pctMap.get(`${r.player_id}:${r.position_bucket}`) ?? null,
  }));

  return { kind: "stat", key: statKey, label: def.label, competitionId, seasonLabel, rows };
}

export async function getCompositeRanking(
  competitionId: number,
  seasonLabel: string,
  compositeKey: string,
  opts: { positionBucket?: string; minMinutes?: number; limit?: number } = {},
): Promise<RankingResult | null> {
  const comp = COMPOSITE_BY_KEY.get(compositeKey);
  if (!comp) return null;
  const client = getSupabaseClient();
  const seasonId = await resolveSeasonId(competitionId, seasonLabel);
  if (seasonId == null) return null;
  const minMinutes = opts.minMinutes ?? 0;

  // composite is built from percentiles -> read the percentile view (threshold applied)
  let q = client.from("player_season_percentiles").select("*").eq("season_id", seasonId).gte("minutes", minMinutes);
  if (opts.positionBucket) q = q.eq("position_bucket", opts.positionBucket);
  const { data, error } = await q;
  if (error) throw error;

  const scored = (data as Row[])
    .map((r) => {
      const vals: number[] = [];
      for (const k of comp.members) {
        const p = dispPct(num(r[`${k}_pct`]), STAT_BY_KEY.get(k)?.lowerIsBetter);
        if (p != null) vals.push(p);
      }
      const score = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
      return { row: r, score };
    })
    .filter((x) => x.score != null);

  const deduped = dedupePlayers(scored.map((x) => ({ ...x.row, __score: x.score })) as Row[]);
  const names = await namesFor(client, deduped.map((r) => r.player_id as number));
  deduped.sort((a, b) => (b.__score as number) - (a.__score as number));

  const rows: RankRow[] = deduped.slice(0, opts.limit ?? 100).map((r, i) => ({
    rank: i + 1,
    playerId: r.player_id as number,
    name: names.get(r.player_id as number) ?? String(r.player_id),
    positionBucket: r.position_bucket as string,
    minutes: r.minutes as number,
    value: Math.round((r.__score as number) * 10) / 10,
    percentile: Math.round(r.__score as number),
  }));

  return { kind: "composite", key: compositeKey, label: comp.label, competitionId, seasonLabel, rows };
}

export interface ScatterPoint {
  playerId: number;
  name: string;
  competitionId: number;
  x: number | null;
  y: number | null;
  minutes: number;
}

export interface ScatterResult {
  seasonLabel: string;
  x: { key: string; label: string };
  y: { key: string; label: string };
  points: ScatterPoint[];
}

export async function getScatter(
  seasonLabel: string,
  xKey: string,
  yKey: string,
  opts: { minMinutes?: number } = {},
): Promise<ScatterResult | null> {
  const xDef = STAT_BY_KEY.get(xKey);
  const yDef = STAT_BY_KEY.get(yKey);
  if (!xDef || !yDef) return null;
  const client = getSupabaseClient();
  const minMinutes = opts.minMinutes ?? 0;

  // all competitions' seasons sharing this label
  const { data: seasons } = await client.from("seasons").select("id,competition_id").eq("season_label", seasonLabel);
  if (!seasons || seasons.length === 0) return null;
  const seasonToComp = new Map<number, number>(
    seasons.map((s) => [s.id as number, s.competition_id as number]),
  );

  const { data, error } = await client
    .from("player_season_stats")
    .select(`player_id,season_id,minutes,${xKey},${yKey}`)
    .in("season_id", Array.from(seasonToComp.keys()))
    .gte("minutes", minMinutes);
  if (error) throw error;

  const deduped = dedupePlayers(data as unknown as Row[]);
  const names = await namesFor(client, deduped.map((r) => r.player_id as number));
  const points: ScatterPoint[] = deduped.map((r) => ({
    playerId: r.player_id as number,
    name: names.get(r.player_id as number) ?? String(r.player_id),
    competitionId: seasonToComp.get(r.season_id as number) ?? 0,
    x: num(r[xKey]),
    y: num(r[yKey]),
    minutes: r.minutes as number,
  }));

  return {
    seasonLabel,
    x: { key: xKey, label: xDef.label },
    y: { key: yKey, label: yDef.label },
    points,
  };
}

export async function getTeamsForSeason(
  competitionId: number,
  seasonLabel: string,
): Promise<{ seasonId: number; teams: TeamRow[] } | null> {
  const client = getSupabaseClient();
  const seasonId = await resolveSeasonId(competitionId, seasonLabel);
  if (seasonId == null) return null;
  const { data: rows, error } = await client
    .from("team_season_stats")
    .select("*")
    .eq("competition_id", competitionId)
    .eq("season_id", seasonId);
  if (error) throw error;
  const teamIds = (rows as Row[]).map((r) => r.team_id as number);
  const { data: teams } = await client.from("teams").select("id,name").in("id", teamIds);
  const nameById = new Map<number, string>(
    (teams ?? []).map((t) => [t.id as number, t.name as string]),
  );
  const out: TeamRow[] = (rows as Row[]).map((r) => {
    const matches = (r.matches_played as number) ?? 0;
    return {
      teamId: r.team_id as number,
      name: nameById.get(r.team_id as number) ?? String(r.team_id),
      matchesPlayed: matches,
      stats: aggLines(r, matches),
    };
  });
  out.sort((a, b) => a.name.localeCompare(b.name));
  return { seasonId, teams: out };
}
