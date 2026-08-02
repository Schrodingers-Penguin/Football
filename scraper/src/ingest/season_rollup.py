"""Season rollup: player_match_stats -> player_season_stats.

Reads every match-stat row for a season, aggregates per player (per-90s,
percentages, dominant position), and upserts the season rows. Idempotent:
re-running recomputes from scratch, overwrites on the
(season_id, player_id, position_bucket) unique key, and prunes bucket rows the
rollup no longer emits — the upsert alone cannot remove those, so without the
prune a player's dropped bucket keeps stale season totals indefinitely.

Separate from per-match ingest by design — a season row depends on *all* of a
player's matches, so it is recomputed in bulk after backfill (and by the daily
job once that lands), not incrementally per match.
"""

import time

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
            .order("id")  # stable order — paginating without it drops/dupes rows
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
    pruned = writers.prune_player_season_stats(client, season_id, rows)

    summary = {
        "season_id": season_id,
        "match_stat_rows": len(match_stats),
        "player_season_rows": len(rows),
        "pruned_rows": pruned,
    }
    log(
        f"season {season_id}: {len(rows)} players from {len(match_stats)} match-stat rows"
        + (f" ({pruned} stale bucket rows pruned)" if pruned else "")
    )
    return summary


# One RPC per materialized view, cheapest first. Refreshing all three in a
# single call (the old refresh_dashboard_views RPC) put them on one shared
# statement_timeout budget, which the 02:00 UTC cron exceeded every night —
# see db/migrations/20260802010000_split_refresh.sql.
_VIEW_REFRESH_RPCS = (
    "refresh_player_season_percentiles",
    "refresh_team_season_stats",
    "refresh_league_season_stats",
)


def refresh_dashboard_views(client=None, log=print, retries: int = 1) -> None:
    """Refresh the materialized dashboard views (percentiles, team/league aggregates)
    after a rollup.

    One RPC per view so each gets its own statement_timeout budget, and one retry
    apiece — a timed-out refresh leaves its pages warm, so the second attempt is
    much faster than the first.

    Raises if any view is still stale afterwards. This used to swallow the error
    and log "view refresh skipped", which is how six nights of stale percentiles
    went unnoticed: the scrape was green and the dashboard was wrong.
    """
    from ..db import get_client

    client = client or get_client()
    failures: list[str] = []
    for rpc in _VIEW_REFRESH_RPCS:
        for attempt in range(retries + 1):
            started = time.monotonic()
            try:
                client.rpc(rpc).execute()
                log(f"{rpc}: refreshed in {time.monotonic() - started:.1f}s")
                break
            except Exception as e:  # noqa: BLE001 — retry any failure, then report
                elapsed = time.monotonic() - started
                if attempt < retries:
                    log(f"{rpc}: failed after {elapsed:.1f}s, retrying ({e})")
                else:
                    log(f"{rpc}: FAILED after {elapsed:.1f}s ({e})")
                    failures.append(f"{rpc}: {e}")
    if failures:
        raise RuntimeError(
            "dashboard views are stale — the dashboard is now serving old numbers:\n  "
            + "\n  ".join(failures)
        )


def rollup_all_seasons(*, client=None, log=print) -> list[dict]:
    """Rollup every season that has at least one row in `seasons`."""
    from ..db import get_client

    client = client or get_client()
    season_ids = [s["id"] for s in client.table("seasons").select("id").execute().data]
    return [rollup_season(sid, client=client, log=log) for sid in season_ids]
