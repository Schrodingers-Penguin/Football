"""Season rollup: player_match_stats -> player_season_stats.

Reads every match-stat row for a season, aggregates per player (per-90s,
percentages, dominant position), and upserts the season rows. Idempotent:
re-running recomputes from scratch and overwrites on the
(season_id, player_id, position_bucket) unique key.

Separate from per-match ingest by design — a season row depends on *all* of a
player's matches, so it is recomputed in bulk after backfill (and by the daily
job once that lands), not incrementally per match.
"""

from ..aggregate.season import build_player_season_rows
from . import writers

_PAGE = 1000  # PostgREST hard-caps a single response at 1000 rows


def _fetch_season_match_stats(client, season_id: int) -> list[dict]:
    """All player_match_stats rows whose match belongs to this season.

    Filters via the embedded `matches` FK so we never have to pass a long list
    of match ids. Paginates because PostgREST caps each response at 1000 rows.
    """
    rows: list[dict] = []
    start = 0
    while True:
        res = (
            client.table("player_match_stats")
            .select("*, matches!inner(season_id)")
            .eq("matches.season_id", season_id)
            .range(start, start + _PAGE - 1)
            .execute()
        )
        batch = res.data or []
        rows.extend(batch)
        if len(batch) < _PAGE:
            break
        start += _PAGE
    return rows


def rollup_season(season_id: int, *, client=None, log=print) -> dict:
    """Recompute and upsert all player_season_stats rows for one season."""
    from ..db import get_client

    client = client or get_client()

    match_stats = _fetch_season_match_stats(client, season_id)
    rows = build_player_season_rows(match_stats, season_id=season_id)
    writers.upsert_player_season_stats(client, rows)

    summary = {
        "season_id": season_id,
        "match_stat_rows": len(match_stats),
        "player_season_rows": len(rows),
    }
    log(f"season {season_id}: {len(rows)} players from {len(match_stats)} match-stat rows")
    return summary


def refresh_dashboard_views(client=None, log=print) -> None:
    """Refresh the materialized dashboard views (percentiles, team/league aggregates)
    after a rollup. Tolerant if the DB function isn't present yet."""
    from ..db import get_client

    client = client or get_client()
    try:
        client.rpc("refresh_dashboard_views").execute()
        log("refreshed dashboard materialized views")
    except Exception as e:  # noqa: BLE001 — refresh is best-effort
        log(f"view refresh skipped ({e})")


def rollup_all_seasons(*, client=None, log=print) -> list[dict]:
    """Rollup every season that has at least one row in `seasons`."""
    from ..db import get_client

    client = client or get_client()
    season_ids = [s["id"] for s in client.table("seasons").select("id").execute().data]
    return [rollup_season(sid, client=client, log=log) for sid in season_ids]
