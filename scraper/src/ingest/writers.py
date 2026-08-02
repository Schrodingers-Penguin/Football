"""Idempotent writes to Supabase Postgres via the service-role client.

All upserts so re-ingesting a match is safe. Conflict targets match the schema's
UNIQUE constraints (SPEC §6).
"""

from datetime import UTC, datetime

_PAGE = 1000  # PostgREST hard-caps a single response at 1000 rows


def get_or_create_season(client, competition_id: int, season_label: str) -> int:
    """Return seasons.id for (competition, label), creating the row if absent."""
    res = (
        client.table("seasons")
        .upsert(
            {"competition_id": competition_id, "season_label": season_label},
            on_conflict="competition_id,season_label",
        )
        .execute()
    )
    return res.data[0]["id"]


def upsert_teams(client, teams: list[dict]) -> None:
    if teams:
        client.table("teams").upsert(teams).execute()  # conflict on PK id


def upsert_players(client, players: list[dict]) -> None:
    if players:
        client.table("players").upsert(players).execute()  # conflict on PK id


def upsert_match(client, match_row: dict) -> None:
    client.table("matches").upsert(match_row).execute()  # conflict on PK id


def upsert_player_match_stats(client, rows: list[dict]) -> None:
    if rows:
        client.table("player_match_stats").upsert(rows, on_conflict="match_id,player_id").execute()


def upsert_player_season_stats(client, rows: list[dict]) -> None:
    if rows:
        client.table("player_season_stats").upsert(
            rows, on_conflict="season_id,player_id,position_bucket"
        ).execute()


def prune_player_season_stats(client, season_id: int, rows: list[dict]) -> int:
    """Delete season rows for buckets the rollup no longer emits.

    The upsert conflict key is (season_id, player_id, position_bucket), so it only
    overwrites buckets still being written. A player's eligible buckets shrink as
    the season goes on (SPEC §7: a role needs >=25% of season minutes), and the
    dropped bucket's row was left behind holding whatever season totals were
    current the last time it qualified — stale minutes *and* stale per-90s.

    Call after the upsert, so a season is never momentarily empty.

    No-ops on empty `rows`: a season with matches always yields players, so an
    empty rollup means the source fetch failed, and pruning against it would
    delete every row for the season.
    """
    if not rows:
        return 0
    keep = {(r["player_id"], r["position_bucket"]) for r in rows}

    existing: list[dict] = []
    start = 0
    while True:
        res = (
            client.table("player_season_stats")
            .select("id,player_id,position_bucket")
            .eq("season_id", season_id)
            .order("id")  # stable order — paginating without it drops/dupes rows
            .range(start, start + _PAGE - 1)
            .execute()
        )
        batch = res.data or []
        existing.extend(batch)
        if len(batch) < _PAGE:
            break
        start += _PAGE

    stale = [r["id"] for r in existing if (r["player_id"], r["position_bucket"]) not in keep]
    for i in range(0, len(stale), _PAGE):
        client.table("player_season_stats").delete().in_("id", stale[i : i + _PAGE]).execute()
    return len(stale)


def mark_ingested(client, match_id: int, raw_json_path: str) -> None:
    client.table("matches").update(
        {"raw_json_path": raw_json_path, "ingested_at": datetime.now(UTC).isoformat()}
    ).eq("id", match_id).execute()


def is_ingested(client, match_id: int) -> bool:
    """True if the match already has a completed ingest (ingested_at set)."""
    res = client.table("matches").select("ingested_at").eq("id", match_id).execute()
    return bool(res.data and res.data[0].get("ingested_at"))
