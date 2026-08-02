/**
 * Server-side data access (Supabase service role). Import only in API routes /
 * server components — never in a 'use client' file.
 */
import { getSupabaseClient } from "@/lib/supabase";
import { COMPOSITE_BY_KEY, COMPOSITES } from "@/lib/composites";
import { STAT_BY_KEY, STAT_CATALOG, TEAM_STAT_CATALOG, type StatDef } from "@/lib/stats";

function dispPct(pct: number | null, lowerIsBetter?: boolean): number | null {
  if (pct == null) return null;
  return lowerIsBetter ? 100 - pct : pct;
}

type Row = Record<string, unknown>;

function num(v: unknown): number | null {
  return typeof v === "number" ? v : null;
}

/** Page past Supabase's 1000-row response cap. Pages are fetched in parallel
 *  batches (sequential pagination over many leagues was ~12 round-trips ≈ 8s). */
async function fetchAllRows(
  make: (from: number, to: number) => PromiseLike<{ data: unknown[] | null; error: unknown }>,
): Promise<Row[]> {
  const size = 1000;
  const batchPages = 8;
  const page = async (i: number): Promise<Row[]> => {
    const { data, error } = await make(i * size, i * size + size - 1);
    if (error) throw error;
    return (data ?? []) as unknown as Row[];
  };

  const first = await page(0);
  if (first.length < size) return first;

  const out = [...first];
  let base = 1;
  for (;;) {
    const batch = await Promise.all(Array.from({ length: batchPages }, (_, i) => page(base + i)));
    let reachedEnd = false;
    for (const b of batch) {
      out.push(...b);
      if (b.length < size) reachedEnd = true;
    }
    if (reachedEnd) break;
    base += batchPages;
  }
  return out;
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
  qualified: boolean; // met the minutes threshold => part of the peer pool
  belowThreshold: boolean; // ranked vs the pool but excluded from it
  stats: StatLine[];
}

/** Ascending percentile of a below-threshold player vs the qualifying pool
 *  (they are not in the pool). */
function pctVsPool(playerRow: Row, poolRows: Row[]): Map<string, number> {
  const m = new Map<string, number>();
  for (const s of STAT_CATALOG) {
    const pv = num(playerRow[s.key]);
    if (pv == null) continue;
    const vals = poolRows.map((r) => num(r[s.key])).filter((v): v is number => v != null);
    if (!vals.length) continue;
    m.set(s.key, (vals.filter((v) => v < pv).length / vals.length) * 100);
  }
  return m;
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
  // accent-insensitive via the unaccent RPC ("Odegaard" -> "Ødegaard")
  const { data, error } = await client.rpc("search_players", { q, lim: limit });
  if (!error && data) {
    return (data as Row[]).map((r) => ({ id: r.id as number, name: r.name as string }));
  }
  // fallback if the migration isn't applied yet (accent-sensitive)
  const { data: d2 } = await client
    .from("players")
    .select("id,name")
    .ilike("name", `%${q}%`)
    .order("name")
    .limit(limit);
  return (d2 ?? []).map((r) => ({ id: r.id as number, name: r.name as string }));
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
  // most recent season first, so a freshly-searched player defaults to it
  options.sort((a, b) => b.seasonLabel.localeCompare(a.seasonLabel) || b.minutes - a.minutes);
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

  // A below-threshold player isn't in the view; rank them vs the qualifying
  // pool (without joining it). Fetch the season's minutes threshold and, per
  // bucket, the qualifying rows to compare against.
  const { data: cfg } = await client
    .from("percentile_config")
    .select("minutes_threshold")
    .eq("season_id", seasonId)
    .maybeSingle();
  const threshold = cfg ? (cfg.minutes_threshold as number) : Number.POSITIVE_INFINITY;

  const poolPctByBucket = new Map<string, Map<string, number>>();
  for (const sr of statRows as Row[]) {
    const bucket = sr.position_bucket as string;
    if (pctByBucket.has(bucket)) continue; // qualifying — use the view
    const { data: poolRows } = await client
      .from("player_season_stats")
      .select("*")
      .eq("season_id", seasonId)
      .eq("position_bucket", bucket)
      .gte("minutes", threshold);
    poolPctByBucket.set(bucket, pctVsPool(sr, (poolRows ?? []) as Row[]));
  }

  const pools: ScoutingPool[] = (statRows as Row[])
    .map((sr) => {
      const bucket = sr.position_bucket as string;
      const viewPct = pctByBucket.get(bucket);
      const poolPct = poolPctByBucket.get(bucket);
      const stats: StatLine[] = STAT_CATALOG.map((s) => ({
        key: s.key,
        value: num(sr[s.key]),
        percentile: viewPct ? num(viewPct[`${s.key}_pct`]) : (poolPct?.get(s.key) ?? null),
      }));
      return {
        positionBucket: bucket,
        minutes: sr.minutes as number,
        positionMinutes: num(sr.position_minutes),
        qualified: viewPct != null,
        belowThreshold: viewPct == null,
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
  competitionId: number;
  positionBucket: string;
  minutes: number;
  value: number | null;
  percentile: number | null;
}

export interface RankingResult {
  kind: "stat" | "composite";
  key: string;
  label: string;
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

/** season_id -> competition_id for the given competitions + season label. */
async function resolveSeasonIds(
  client: ReturnType<typeof getSupabaseClient>,
  competitionIds: number[],
  seasonLabel: string,
): Promise<Map<number, number>> {
  const { data } = await client
    .from("seasons")
    .select("id,competition_id")
    .eq("season_label", seasonLabel)
    .in("competition_id", competitionIds);
  return new Map((data ?? []).map((s) => [s.id as number, s.competition_id as number]));
}

/** `${player_id}:${season_id}` -> primary bucket (most position-minutes), so a
 *  player appears only in the ranking of their primary position. */
async function primaryBuckets(
  client: ReturnType<typeof getSupabaseClient>,
  seasonIds: number[],
): Promise<Map<string, string>> {
  const data = await fetchAllRows((from, to) =>
    client
      .from("player_season_stats")
      .select("player_id,season_id,position_bucket,position_minutes")
      .in("season_id", seasonIds)
      .order("id")
      .range(from, to),
  );
  const best = new Map<string, { bucket: string; pm: number }>();
  for (const r of data) {
    const key = `${r.player_id}:${r.season_id}`;
    const pm = (r.position_minutes as number) ?? 0;
    const cur = best.get(key);
    if (!cur || pm > cur.pm) best.set(key, { bucket: r.position_bucket as string, pm });
  }
  return new Map(Array.from(best, ([k, v]) => [k, v.bucket]));
}

export async function getStatRanking(
  competitionIds: number[],
  seasonLabel: string,
  statKey: string,
  opts: { positionBucket?: string; minMinutes?: number; limit?: number } = {},
): Promise<RankingResult | null> {
  const def = STAT_BY_KEY.get(statKey);
  if (!def) return null;
  const client = getSupabaseClient();
  const seasonMap = await resolveSeasonIds(client, competitionIds, seasonLabel);
  if (seasonMap.size === 0) return null;
  const seasonIds = Array.from(seasonMap.keys());
  const minMinutes = opts.minMinutes ?? 0;

  const pctCol = `${statKey}_pct`;
  // Fetch all buckets (with position_minutes) so primary is computed from the
  // same rows — avoids a second full-table scan.
  const [data, pctData] = await Promise.all([
    fetchAllRows((from, to) =>
      client
        .from("player_season_stats")
        .select(`player_id,season_id,position_bucket,position_minutes,minutes,${statKey}`)
        .in("season_id", seasonIds)
        .gte("minutes", minMinutes)
        .order("id")
        .range(from, to),
    ),
    fetchAllRows((from, to) =>
      client
        .from("player_season_percentiles")
        .select(`player_id,season_id,position_bucket,${pctCol}`)
        .in("season_id", seasonIds)
        .order("season_id")
        .order("player_id")
        .order("position_bucket")
        .range(from, to),
    ),
  ]);

  const pctMap = new Map<string, number | null>(
    pctData.map((r) => [`${r.player_id}:${r.season_id}:${r.position_bucket}`, num(r[pctCol])]),
  );

  const primary = new Map<string, { bucket: string; pm: number }>();
  for (const r of data) {
    const key = `${r.player_id}:${r.season_id}`;
    const pm = (r.position_minutes as number) ?? 0;
    const cur = primary.get(key);
    if (!cur || pm > cur.pm) primary.set(key, { bucket: r.position_bucket as string, pm });
  }

  // keep each player's primary-bucket row only (and matching the position filter)
  const kept = data.filter((r) => {
    const prim = primary.get(`${r.player_id}:${r.season_id}`)?.bucket;
    if (r.position_bucket !== prim) return false;
    if (opts.positionBucket && r.position_bucket !== opts.positionBucket) return false;
    return num(r[statKey]) != null;
  });

  const sign = def.lowerIsBetter ? 1 : -1;
  kept.sort((a, b) => sign * ((num(a[statKey]) ?? 0) - (num(b[statKey]) ?? 0)));

  // names only for the rows we return (a 2500-id .in() took ~8s)
  const top = kept.slice(0, opts.limit ?? 100);
  const names = await namesFor(client, top.map((r) => r.player_id as number));
  const rows: RankRow[] = top.map((r, i) => ({
    rank: i + 1,
    playerId: r.player_id as number,
    name: names.get(r.player_id as number) ?? String(r.player_id),
    competitionId: seasonMap.get(r.season_id as number) ?? 0,
    positionBucket: r.position_bucket as string,
    minutes: r.minutes as number,
    value: num(r[statKey]),
    percentile: pctMap.get(`${r.player_id}:${r.season_id}:${r.position_bucket}`) ?? null,
  }));

  return { kind: "stat", key: statKey, label: def.label, seasonLabel, rows };
}

export async function getCompositeRanking(
  competitionIds: number[],
  seasonLabel: string,
  compositeKey: string,
  opts: { positionBucket?: string; minMinutes?: number; limit?: number } = {},
): Promise<RankingResult | null> {
  const comp = COMPOSITE_BY_KEY.get(compositeKey);
  if (!comp) return null;
  const client = getSupabaseClient();
  const seasonMap = await resolveSeasonIds(client, competitionIds, seasonLabel);
  if (seasonMap.size === 0) return null;
  const seasonIds = Array.from(seasonMap.keys());
  const minMinutes = opts.minMinutes ?? 0;

  const [data, primary] = await Promise.all([
    fetchAllRows((from, to) =>
      client
        .from("player_season_percentiles")
        .select("*")
        .in("season_id", seasonIds)
        .gte("minutes", minMinutes)
        .order("season_id")
        .order("player_id")
        .order("position_bucket")
        .range(from, to),
    ),
    primaryBuckets(client, seasonIds),
  ]);

  const scored = data
    .filter((r) => {
      const prim = primary.get(`${r.player_id}:${r.season_id}`);
      if (r.position_bucket !== prim) return false;
      return !opts.positionBucket || r.position_bucket === opts.positionBucket;
    })
    .map((r) => {
      const vals: number[] = [];
      for (const k of comp.members) {
        const p = dispPct(num(r[`${k}_pct`]), STAT_BY_KEY.get(k)?.lowerIsBetter);
        if (p != null) vals.push(p);
      }
      const score = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
      return { row: r, score };
    })
    .filter((x): x is { row: Row; score: number } => x.score != null);

  scored.sort((a, b) => b.score - a.score);
  const top = scored.slice(0, opts.limit ?? 100);
  const names = await namesFor(client, top.map((x) => x.row.player_id as number));

  const rows: RankRow[] = top.map((x, i) => ({
    rank: i + 1,
    playerId: x.row.player_id as number,
    name: names.get(x.row.player_id as number) ?? String(x.row.player_id),
    competitionId: seasonMap.get(x.row.season_id as number) ?? 0,
    positionBucket: x.row.position_bucket as string,
    minutes: x.row.minutes as number,
    value: Math.round(x.score * 10) / 10,
    percentile: Math.round(x.score),
  }));

  return { kind: "composite", key: compositeKey, label: comp.label, seasonLabel, rows };
}

export interface ExplorerRow {
  playerId: number;
  name: string;
  competitionId: number;
  positionBucket: string;
  minutes: number;
  /** raw value per selected stat key */
  values: Record<string, number | null>;
  /** display percentile per selected stat key (lowerIsBetter already inverted) */
  percentiles: Record<string, number | null>;
}

export interface ExplorerResult {
  seasonLabel: string;
  statKeys: string[];
  rows: ExplorerRow[];
  /** rows matching the filters before `limit` was applied */
  matched: number;
}

/**
 * Multi-stat player table: any subset of the catalogue as columns, filtered by
 * league scope / position / minutes / per-stat minimums, sorted by any column.
 *
 * Same pool semantics as the rankings: one row per player, their primary bucket
 * (most position-minutes), so a hybrid isn't listed twice.
 */
export async function getPlayerExplorer(
  competitionIds: number[],
  seasonLabel: string,
  statKeys: string[],
  opts: {
    positionBucket?: string;
    minMinutes?: number;
    /** stat key, or "minutes" */
    sortKey?: string;
    sortDir?: "asc" | "desc";
    /** stat key -> minimum raw value */
    minValues?: Record<string, number>;
    limit?: number;
  } = {},
): Promise<ExplorerResult | null> {
  // only known keys reach the select string
  const defs = statKeys.map((k) => STAT_BY_KEY.get(k)).filter((d): d is StatDef => !!d);
  const keys = defs.map((d) => d.key);
  const client = getSupabaseClient();
  const seasonMap = await resolveSeasonIds(client, competitionIds, seasonLabel);
  if (seasonMap.size === 0) return null;
  const seasonIds = Array.from(seasonMap.keys());
  const minMinutes = opts.minMinutes ?? 0;

  const statCols = keys.length ? `,${keys.join(",")}` : "";
  const pctCols = keys.length ? `,${keys.map((k) => `${k}_pct`).join(",")}` : "";

  const [data, pctData] = await Promise.all([
    fetchAllRows((from, to) =>
      client
        .from("player_season_stats")
        .select(`player_id,season_id,position_bucket,position_minutes,minutes${statCols}`)
        .in("season_id", seasonIds)
        .gte("minutes", minMinutes)
        .order("id")
        .range(from, to),
    ),
    fetchAllRows((from, to) =>
      client
        .from("player_season_percentiles")
        .select(`player_id,season_id,position_bucket${pctCols}`)
        .in("season_id", seasonIds)
        .order("season_id")
        .order("player_id")
        .order("position_bucket")
        .range(from, to),
    ),
  ]);

  const pctMap = new Map<string, Row>(
    pctData.map((r) => [`${r.player_id}:${r.season_id}:${r.position_bucket}`, r]),
  );

  // primary bucket from the same rows — avoids a second full-table scan
  const primary = new Map<string, { bucket: string; pm: number }>();
  for (const r of data) {
    const k = `${r.player_id}:${r.season_id}`;
    const pm = (r.position_minutes as number) ?? 0;
    const cur = primary.get(k);
    if (!cur || pm > cur.pm) primary.set(k, { bucket: r.position_bucket as string, pm });
  }

  const minValues = opts.minValues ?? {};
  const kept = data.filter((r) => {
    if (r.position_bucket !== primary.get(`${r.player_id}:${r.season_id}`)?.bucket) return false;
    if (opts.positionBucket && r.position_bucket !== opts.positionBucket) return false;
    for (const [k, min] of Object.entries(minValues)) {
      const v = num(r[k]);
      if (v == null || v < min) return false;
    }
    return true;
  });

  const sortKey = opts.sortKey ?? keys[0] ?? "minutes";
  const sortDef = STAT_BY_KEY.get(sortKey);
  // default to best-first: ascending for lower-is-better stats, descending otherwise
  const dir = opts.sortDir ?? (sortDef?.lowerIsBetter ? "asc" : "desc");
  const sign = dir === "asc" ? 1 : -1;
  kept.sort((a, b) => {
    const av = num(a[sortKey]);
    const bv = num(b[sortKey]);
    if (av == null && bv == null) return 0;
    if (av == null) return 1; // nulls last, either direction
    if (bv == null) return -1;
    return sign * (av - bv);
  });

  const top = kept.slice(0, opts.limit ?? 100);
  const names = await namesFor(client, top.map((r) => r.player_id as number));

  const rows: ExplorerRow[] = top.map((r) => {
    const pct = pctMap.get(`${r.player_id}:${r.season_id}:${r.position_bucket}`);
    const values: Record<string, number | null> = {};
    const percentiles: Record<string, number | null> = {};
    for (const d of defs) {
      values[d.key] = num(r[d.key]);
      percentiles[d.key] = dispPct(pct ? num(pct[`${d.key}_pct`]) : null, d.lowerIsBetter);
    }
    return {
      playerId: r.player_id as number,
      name: names.get(r.player_id as number) ?? String(r.player_id),
      competitionId: seasonMap.get(r.season_id as number) ?? 0,
      positionBucket: r.position_bucket as string,
      minutes: r.minutes as number,
      values,
      percentiles,
    };
  });

  return { seasonLabel, statKeys: keys, rows, matched: kept.length };
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

  // embed the player name via the FK join — avoids a slow giant .in() on names
  const data = await fetchAllRows((from, to) =>
    client
      .from("player_season_stats")
      .select(`player_id,season_id,minutes,${xKey},${yKey},players(name)`)
      .in("season_id", Array.from(seasonToComp.keys()))
      .gte("minutes", minMinutes)
      .order("id")
      .range(from, to),
  );

  const deduped = dedupePlayers(data);
  const points: ScatterPoint[] = deduped.map((r) => ({
    playerId: r.player_id as number,
    name: (r.players as { name?: string } | null)?.name ?? String(r.player_id),
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

const ALL_LEAGUES = [2, 3, 4, 5, 13, 21, 22];

export interface SimilarPlayer {
  playerId: number;
  name: string;
  competitionId: number;
  similarity: number;
}

/** Players most similar to the target by percentile vector, within the target's
 *  primary position, across all leagues for the same season. */
export async function getSimilarPlayers(
  playerId: number,
  competitionId: number,
  seasonLabel: string,
  limit = 10,
): Promise<{ positionBucket: string; players: SimilarPlayer[] } | null> {
  const client = getSupabaseClient();
  const seasonId = await resolveSeasonId(competitionId, seasonLabel);
  if (seasonId == null) return null;

  const { data: prows } = await client
    .from("player_season_stats")
    .select("position_bucket,position_minutes")
    .eq("season_id", seasonId)
    .eq("player_id", playerId);
  if (!prows || prows.length === 0) return null;
  const primary = (prows as Row[]).sort(
    (a, b) => ((b.position_minutes as number) ?? 0) - ((a.position_minutes as number) ?? 0),
  )[0].position_bucket as string;

  const seasonMap = await resolveSeasonIds(client, ALL_LEAGUES, seasonLabel);
  const seasonIds = Array.from(seasonMap.keys());
  const rows = await fetchAllRows((from, to) =>
    client
      .from("player_season_percentiles")
      .select("*")
      .in("season_id", seasonIds)
      .eq("position_bucket", primary)
      .order("season_id")
      .order("player_id")
      .order("position_bucket")
      .range(from, to),
  );

  const target = rows.find((r) => r.player_id === playerId && r.season_id === seasonId);
  if (!target) return { positionBucket: primary, players: [] }; // below threshold: no vector

  const keys = STAT_CATALOG.map((s) => `${s.key}_pct`);
  const vec = (r: Row) => keys.map((k) => num(r[k]) ?? 50);
  const tv = vec(target);
  const maxDist = Math.sqrt(keys.length) * 100;

  const scored = rows
    .filter((r) => !(r.player_id === playerId && r.season_id === seasonId))
    .map((r) => {
      const v = vec(r);
      let s = 0;
      for (let i = 0; i < tv.length; i++) s += (tv[i] - v[i]) ** 2;
      return { r, sim: 100 * (1 - Math.sqrt(s) / maxDist) };
    })
    .sort((a, b) => b.sim - a.sim)
    .slice(0, limit);

  const names = await namesFor(client, scored.map((x) => x.r.player_id as number));
  return {
    positionBucket: primary,
    players: scored.map((x) => ({
      playerId: x.r.player_id as number,
      name: names.get(x.r.player_id as number) ?? String(x.r.player_id),
      competitionId: seasonMap.get(x.r.season_id as number) ?? 0,
      similarity: Math.round(x.sim * 10) / 10,
    })),
  };
}

export interface TrendPoint {
  seasonLabel: string;
  competitionId: number;
  composites: Record<string, number | null>;
}

/** A player's composite ratings across the seasons they qualified in (primary
 *  position each season), for a development trend. */
export async function getPlayerTrend(playerId: number): Promise<TrendPoint[]> {
  const client = getSupabaseClient();
  const { data: ss } = await client
    .from("player_season_stats")
    .select("season_id,position_bucket,position_minutes")
    .eq("player_id", playerId);
  if (!ss || ss.length === 0) return [];

  const primaryBySeason = new Map<number, { bucket: string; pm: number }>();
  for (const r of ss as Row[]) {
    const sid = r.season_id as number;
    const pm = (r.position_minutes as number) ?? 0;
    const cur = primaryBySeason.get(sid);
    if (!cur || pm > cur.pm) primaryBySeason.set(sid, { bucket: r.position_bucket as string, pm });
  }
  const seasonIds = Array.from(primaryBySeason.keys());

  const [{ data: view }, { data: seasons }] = await Promise.all([
    // filter on season_id (a partition key) so Postgres prunes partitions —
    // a player_id-only filter recomputes every PERCENT_RANK window (~4s).
    client
      .from("player_season_percentiles")
      .select("*")
      .in("season_id", seasonIds)
      .eq("player_id", playerId),
    client.from("seasons").select("id,season_label,competition_id").in("id", seasonIds),
  ]);
  const meta = new Map<number, { label: string; comp: number }>(
    (seasons ?? []).map((s) => [s.id as number, { label: s.season_label as string, comp: s.competition_id as number }]),
  );

  const points: TrendPoint[] = [];
  for (const sid of seasonIds) {
    const bucket = primaryBySeason.get(sid)!.bucket;
    const row = (view as Row[] | null)?.find(
      (v) => v.season_id === sid && v.position_bucket === bucket,
    );
    if (!row) continue; // below threshold that season
    const composites: Record<string, number | null> = {};
    for (const c of COMPOSITES) {
      const vals = c.members
        .map((k) => dispPct(num(row[`${k}_pct`]), STAT_BY_KEY.get(k)?.lowerIsBetter))
        .filter((v): v is number => v != null);
      composites[c.key] = vals.length
        ? Math.round((vals.reduce((a, b) => a + b, 0) / vals.length) * 10) / 10
        : null;
    }
    const m = meta.get(sid);
    points.push({ seasonLabel: m?.label ?? String(sid), competitionId: m?.comp ?? 0, composites });
  }
  points.sort((a, b) => a.seasonLabel.localeCompare(b.seasonLabel));
  return points;
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
