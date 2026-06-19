"""Reprocess stored match JSONs through the current parser/taggers — no scraping.

Two uses:
  - read events across many matches to fit models that need them (xT);
  - back-populate new metric columns onto already-ingested matches after the
    taggers change.

Raw verbatim matchCentreData lives in Supabase Storage (hybrid storage, SPEC §5);
we download it, re-aggregate, and upsert player_match_stats. Teams/players/match
rows and the stored JSON are untouched (unchanged), so this never re-scrapes and
never re-uploads.

The core loop takes its side effects as injected callables so it is unit-testable
without storage or a DB; `reprocess_all` wires the real readers/writers.
"""

from collections.abc import Callable, Iterable, Iterator


def run_reprocess(
    items: Iterable[dict],
    *,
    process_one: Callable[[dict], int],
    rollup_seasons: Callable[[list[int]], None],
    log: Callable[[str], None] = print,
) -> dict:
    """Reprocess each item; one failure never aborts the run. After all items,
    re-roll-up every season that was touched. Returns a summary.

    Each item is `{"meta": {"id","competition_id","season_id",...}, "match_data": {...}}`.
    `process_one(item)` returns the number of player rows written (may raise).
    """
    summary = {"matches": 0, "rows": 0, "failed": 0}
    seasons: set[int] = set()

    for item in items:
        mid = item["meta"]["id"]
        try:
            n = process_one(item)
            summary["matches"] += 1
            summary["rows"] += n
            seasons.add(item["meta"]["season_id"])
            if summary["matches"] % 200 == 0:
                log(f"  reprocessed {summary['matches']} matches")
        except Exception as e:  # noqa: BLE001 — isolate one match's failure
            summary["failed"] += 1
            log(f"  reprocess failed {mid}: {e}")

    ordered = sorted(seasons)
    rollup_seasons(ordered)
    summary["seasons_rolled"] = len(ordered)
    return summary


def iter_stored_matches(
    client=None,
    *,
    competition_id: int | None = None,
    season_id: int | None = None,
    limit: int | None = None,
    log: Callable[[str], None] = print,
) -> Iterator[dict]:
    """Yield `{"meta", "match_data"}` for ingested matches, downloading each
    stored JSON from Supabase Storage. Optional competition/season filters."""
    from ..db import get_client
    from ..storage import download_raw_match

    client = client or get_client()
    yielded = 0
    start = 0
    page_size = 1000
    while True:
        q = (
            client.table("matches")
            .select("id,competition_id,season_id,raw_json_path")
            .not_.is_("raw_json_path", "null")
        )
        if competition_id is not None:
            q = q.eq("competition_id", competition_id)
        if season_id is not None:
            q = q.eq("season_id", season_id)
        page = q.range(start, start + page_size - 1).execute().data
        if not page:
            return
        for m in page:
            if limit is not None and yielded >= limit:
                return
            try:
                match_data = download_raw_match(m["raw_json_path"], client=client)
            except Exception as e:  # noqa: BLE001
                log(f"  download failed {m['id']}: {e}")
                continue
            yield {"meta": m, "match_data": match_data}
            yielded += 1
        if len(page) < page_size:
            return
        start += page_size


def reprocess_match(item: dict, *, client) -> int:
    """Re-aggregate one stored match and upsert its player_match_stats rows.

    Includes every player who appeared, substitutes included (bucket NULL),
    mirroring the fresh-ingest pipeline. Returns the number of rows written.
    """
    from ..aggregate.match import aggregate_match
    from ..parser.events import parse_events
    from . import writers

    meta = item["meta"]
    events = parse_events(item["match_data"])
    # Includes substitutes (position_bucket NULL) so their contributions count
    # toward player and team/league totals.
    rows = aggregate_match(
        events,
        item["match_data"],
        match_id=meta["id"],
        competition_id=meta["competition_id"],
        season_label="",  # unused by aggregate; row keys come from match_data
    )
    writers.upsert_player_match_stats(client, rows)
    return len(rows)


def reprocess_all(
    *,
    client=None,
    competition_id: int | None = None,
    season_id: int | None = None,
    limit: int | None = None,
    rollup: bool = True,
    log: Callable[[str], None] = print,
) -> dict:
    """Production wiring: read stored JSONs, re-aggregate, upsert, re-roll-up."""
    from ..db import get_client
    from .season_rollup import refresh_dashboard_views, rollup_season

    client = client or get_client()

    items = iter_stored_matches(
        client, competition_id=competition_id, season_id=season_id, limit=limit, log=log
    )

    def rollup_seasons(season_ids: list[int]) -> None:
        if not rollup:
            return
        for sid in season_ids:
            rollup_season(sid, client=client, log=log)

    result = run_reprocess(
        items,
        process_one=lambda item: reprocess_match(item, client=client),
        rollup_seasons=rollup_seasons,
        log=log,
    )
    if rollup:
        refresh_dashboard_views(client=client, log=log)
    return result
