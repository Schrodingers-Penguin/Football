"""Backfill every domestic league-season, end to end and unattended.

For each (competition, season): auto-resolve the fixtures URL, discover the
fixtures, scrape + ingest each match (idempotent/resumable, rate-limited), then
roll the match stats up into season stats. One season failing is logged and
skipped; the run continues.

Champions League (multi-stage) is excluded — handle it separately.

Run on the Mac, not GitHub Actions (SPEC §14). Expect 3-5 days for a full run.

Examples:
  # dry run — resolve + count fixtures for every league-season, no scrape
  python scripts/backfill_all.py --dry-run

  # smoke test — 2 matches per league-season against Supabase
  python scripts/backfill_all.py --limit 2

  # the real thing
  python scripts/backfill_all.py
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import get_client
from src.ingest.backfill import backfill
from src.ingest.matrix import SeasonJob, build_jobs, run_matrix
from src.ingest.season_rollup import rollup_season
from src.ingest.writers import get_or_create_season
from src.whoscored.competitions import COMPETITION_REGIONS, discover_season_fixtures_url
from src.whoscored.fixtures import discover_fixtures

# All 7 domestic leagues (CL excluded — multi-stage), newest season first.
COMPETITIONS = sorted(COMPETITION_REGIONS)
SEASONS = ["2025-2026", "2024-2025", "2023-2024"]
# PL 2025-26 is already complete; skip the re-discovery (re-ingest would skip
# anyway, but no need to crawl its fixtures page again).
SKIP = {(2, "2025-2026")}


def main() -> None:
    ap = argparse.ArgumentParser(description="Backfill all domestic league-seasons.")
    ap.add_argument("--delay", type=float, default=30.0, help="seconds between scrapes")
    ap.add_argument("--limit", type=int, default=None, help="cap matches per league-season")
    ap.add_argument("--headed", action="store_true", help="show the browser window")
    ap.add_argument("--dry-run", action="store_true", help="resolve + count only; no scrape")
    ap.add_argument(
        "--include-pl-current",
        action="store_true",
        help="don't skip PL 2025-26 (re-discovers it; matches re-ingest is still idempotent)",
    )
    args = ap.parse_args()

    headless = not args.headed
    skip = set() if args.include_pl_current else SKIP
    jobs = build_jobs(COMPETITIONS, SEASONS, skip=skip)

    def resolve_and_discover(job: SeasonJob):
        url = discover_season_fixtures_url(
            job.competition_id, job.season_label, headless=headless
        )
        if not url:
            raise RuntimeError("could not resolve fixtures URL")
        fixtures = discover_fixtures(
            url, job.competition_id, job.season_label, headless=headless
        )
        if args.limit:
            fixtures = fixtures[: args.limit]
        return url, fixtures

    def process_one(job: SeasonJob) -> dict:
        url, fixtures = resolve_and_discover(job)
        if args.dry_run:
            return {"fixtures_url": url, "discovered": len(fixtures), "dry_run": True}

        summary = backfill(fixtures, delay_seconds=args.delay, headless=headless)

        client = get_client()
        season_id = get_or_create_season(client, job.competition_id, job.season_label)
        roll = rollup_season(season_id, client=client)
        return {"matches": summary, "rollup": roll}

    banner = f"{len(jobs)} league-seasons to process (CL excluded)"
    print(banner + (" — DRY RUN" if args.dry_run else ""))
    results = run_matrix(jobs, process_one=process_one)

    ok = sum(1 for r in results if r["status"] == "ok")
    failed = [r for r in results if r["status"] == "failed"]
    print(f"\n=== matrix complete: {ok}/{len(results)} ok, {len(failed)} failed ===")
    for r in failed:
        print(f"  FAILED comp {r['job'].competition_id} {r['job'].season_label}: {r['error']}")


if __name__ == "__main__":
    main()
