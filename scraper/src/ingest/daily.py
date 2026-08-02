"""Daily incremental update: ingest newly-finished matches in the current season.

For each domestic league's current season: resolve the fixtures URL, scan the
recent calendar for *finished* fixtures only, ingest the ones not already in the
DB (backfill skips the rest), and re-roll-up the season. Reuses the matrix
orchestrator so one league failing never aborts the others.

Designed for low volume (a match-day's worth of games), so it's safe on
GitHub Actions minutes — but GitHub-hosted runners are datacenter IPs that
Cloudflare flags quickly. If the cron starts failing on blocks, switch the
workflow to a self-hosted runner on a residential connection (see the workflow
comment); a residential IP scraped thousands of matches without a block.
"""

import datetime as dt
from collections.abc import Callable

from .matrix import build_jobs, run_matrix


def current_season_label(today: dt.date | None = None) -> str:
    """WhoScored-style label for the season in progress. Seasons roll over in
    July, so e.g. any date Jul 2025–Jun 2026 -> '2025-2026'."""
    d = today or dt.date.today()
    start = d.year if d.month >= 7 else d.year - 1
    return f"{start}-{start + 1}"


def run_daily(
    *,
    season_label: str | None = None,
    delay_seconds: float = 30.0,
    jitter_seconds: float = 20.0,
    months: int = 2,
    headless: bool = True,
    limit: int | None = None,
    log: Callable[[str], None] = print,
) -> list[dict]:
    from ..db import get_client
    from ..schema_check import assert_schema
    from ..whoscored.competitions import COMPETITION_REGIONS, discover_season_fixtures_url
    from ..whoscored.fixtures import discover_finished_fixtures
    from .backfill import backfill
    from .season_rollup import rollup_season
    from .writers import get_or_create_season

    # Fail before scraping anything: migrations are applied by hand, and a
    # skipped one degrades silently (see src/schema_check.py). Cheap, and the
    # cron is the one place drift reliably gets noticed.
    assert_schema(log=log)

    season = season_label or current_season_label()
    jobs = build_jobs(sorted(COMPETITION_REGIONS), [season])

    def process_one(job) -> dict:
        url = discover_season_fixtures_url(job.competition_id, job.season_label, headless=headless)
        if not url:
            # Off-season / before next season's fixtures are published: no-op
            # rather than a failure, so the cron doesn't alert all summer.
            return {"skipped": "no fixtures URL for season yet"}
        fixtures = discover_finished_fixtures(
            url, job.competition_id, job.season_label, headless=headless, months=months
        )
        if limit:
            fixtures = fixtures[:limit]
        summary = backfill(
            fixtures, delay_seconds=delay_seconds, jitter_seconds=jitter_seconds, headless=headless
        )
        client = get_client()
        season_id = get_or_create_season(client, job.competition_id, job.season_label)
        roll = rollup_season(season_id, client=client)
        return {"finished_seen": len(fixtures), "matches": summary, "rollup": roll}

    log(f"daily update for season {season} across {len(jobs)} leagues")
    results = run_matrix(jobs, process_one=process_one, log=log)
    from .season_rollup import refresh_dashboard_views

    refresh_dashboard_views(client=get_client(), log=log)
    return results
