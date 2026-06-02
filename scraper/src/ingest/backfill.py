"""Backfill orchestrator: scrape + ingest a queue of matches.

Design goals (SPEC §11 Phase 4):
  - idempotent  : already-ingested matches are skipped (DB is the source of truth)
  - resumable   : a failed/interrupted match stays un-ingested and is retried on
                  the next run; no separate checkpoint file to corrupt
  - rate-limited: a configurable delay between *scrapes* (skips don't wait)
  - robust      : one match failing never aborts the run; failures are counted
                  and logged, the queue continues

The core loop (`run_backfill`) takes its side effects as injected callables so it
is fully unit-testable without a browser or database. `backfill` wires the real
WhoScored scraper + Supabase writers to it.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Fixture:
    match_id: int
    url: str
    competition_id: int
    season_label: str


def run_backfill(
    fixtures: list[Fixture],
    *,
    is_done: Callable[[Fixture], bool],
    ingest_one: Callable[[Fixture], dict],
    delay_seconds: float = 30.0,
    sleep: Callable[[float], None] = time.sleep,
    log: Callable[[str], None] = print,
) -> dict:
    """Process fixtures in order. Returns a summary of counts.

    `is_done(fx)` -> already ingested? (skip without scraping or waiting)
    `ingest_one(fx)` -> scrape + ingest one match (may raise; raising = failure)
    """
    summary = {"total": len(fixtures), "ingested": 0, "skipped": 0, "failed": 0}
    scraped_any = False

    for i, fx in enumerate(fixtures):
        if is_done(fx):
            summary["skipped"] += 1
            log(f"[{i + 1}/{len(fixtures)}] skip {fx.match_id} (already ingested)")
            continue

        # Rate-limit before each scrape except the very first one we perform.
        if scraped_any:
            sleep(delay_seconds)

        try:
            result = ingest_one(fx)
            summary["ingested"] += 1
            rows = result.get("player_rows", "?")
            log(f"[{i + 1}/{len(fixtures)}] ok   {fx.match_id} ({rows} rows)")
        except Exception as exc:  # noqa: BLE001 — one bad match must not stop the queue
            summary["failed"] += 1
            log(f"[{i + 1}/{len(fixtures)}] FAIL {fx.match_id}: {exc!r}")
        finally:
            scraped_any = True

    log(
        f"backfill done: {summary['ingested']} ingested, "
        f"{summary['skipped']} skipped, {summary['failed']} failed "
        f"of {summary['total']}"
    )
    return summary


def backfill(
    fixtures: list[Fixture],
    *,
    client=None,
    delay_seconds: float = 30.0,
    headless: bool = False,
    log: Callable[[str], None] = print,
) -> dict:
    """Production wiring: real WhoScored scraper + Supabase writers.

    Imports the browser scraper lazily so the orchestrator and its tests don't
    pull in Playwright unless an actual backfill runs.
    """
    import asyncio

    from ..db import get_client
    from ..whoscored.scraper import scrape_match
    from . import writers
    from .pipeline import ingest_match

    client = client or get_client()

    def is_done(fx: Fixture) -> bool:
        return writers.is_ingested(client, fx.match_id)

    def ingest_one(fx: Fixture) -> dict:
        match_data = asyncio.run(scrape_match(fx.url, headless=headless))
        return ingest_match(
            match_data, fx.competition_id, fx.season_label, fx.match_id, client=client
        )

    return run_backfill(
        fixtures,
        is_done=is_done,
        ingest_one=ingest_one,
        delay_seconds=delay_seconds,
        sleep=time.sleep,
        log=log,
    )
