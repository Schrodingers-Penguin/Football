"""Backfill a competition+season: discover fixtures, then scrape + ingest each.

Idempotent and resumable — re-running skips matches already in the DB, so it is
safe to interrupt (Ctrl-C) and restart. Rate-limited per SPEC (default 30s
between scrapes). Run on a local Mac, not GitHub Actions (SPEC §14).

The fixtures URL comes from the WhoScored fixtures page for the season (see
src/whoscored/fixtures.py for the PL 2025-26 example URL).

Examples:
  # dry run — just discover and count, no scraping/ingest
  python scripts/backfill.py --competition 2 --season 2025-2026 --fixtures-url "<url>" --dry-run

  # ingest just the first 3 (smoke test against Supabase)
  python scripts/backfill.py --competition 2 --season 2025-2026 --fixtures-url "<url>" --limit 3

  # full season
  python scripts/backfill.py --competition 2 --season 2025-2026 --fixtures-url "..."
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingest.backfill import backfill
from src.whoscored.fixtures import discover_fixtures


def main() -> None:
    ap = argparse.ArgumentParser(description="Backfill a competition+season into Supabase.")
    ap.add_argument("--competition", type=int, required=True, help="WhoScored competition id")
    ap.add_argument("--season", required=True, help="season label, e.g. 2025-2026")
    ap.add_argument(
        "--fixtures-url", required=True, help="WhoScored fixtures page URL for the season"
    )
    ap.add_argument(
        "--delay", type=float, default=30.0, help="seconds between scrapes (default 30)"
    )
    ap.add_argument("--limit", type=int, default=None, help="only process the first N fixtures")
    ap.add_argument(
        "--headless", action="store_true", help="run browser headless (more Cloudflare risk)"
    )
    ap.add_argument(
        "--dry-run", action="store_true", help="discover + count only; no scrape/ingest"
    )
    args = ap.parse_args()

    print(f"Discovering fixtures for competition {args.competition} {args.season}...")
    fixtures = discover_fixtures(
        args.fixtures_url, args.competition, args.season, headless=args.headless
    )
    print(f"  {len(fixtures)} fixtures discovered")

    if args.limit:
        fixtures = fixtures[: args.limit]
        print(f"  limited to first {len(fixtures)}")

    if args.dry_run:
        for f in fixtures[:5]:
            print(f"    {f.match_id}  {f.url}")
        if len(fixtures) > 5:
            print(f"    ... (+{len(fixtures) - 5} more)")
        print("dry run — nothing ingested")
        return

    summary = backfill(fixtures, delay_seconds=args.delay, headless=args.headless)
    print(f"\n{summary}")


if __name__ == "__main__":
    main()
