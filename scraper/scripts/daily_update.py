"""Daily incremental scrape + ingest of newly-finished matches.

Run by the GitHub Actions cron (see .github/workflows/daily.yml). Ingests only
finished, not-yet-stored matches in the current season for each domestic league,
then re-rolls-up the affected seasons. Idempotent — safe to run repeatedly.

Examples:
  python scripts/daily_update.py
  python scripts/daily_update.py --season 2025-2026 --delay 30 --jitter 20
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingest.daily import run_daily


def main() -> None:
    ap = argparse.ArgumentParser(description="Daily incremental update.")
    ap.add_argument("--season", default=None, help="season label (default: current)")
    ap.add_argument("--delay", type=float, default=30.0, help="seconds between scrapes")
    ap.add_argument("--jitter", type=float, default=20.0, help="random extra 0..N s per scrape")
    ap.add_argument("--months", type=int, default=2, help="recent calendar months to scan")
    ap.add_argument("--headed", action="store_true", help="show the browser window")
    ap.add_argument("--limit", type=int, default=None, help="cap matches per league (debug)")
    args = ap.parse_args()

    results = run_daily(
        season_label=args.season,
        delay_seconds=args.delay,
        jitter_seconds=args.jitter,
        months=args.months,
        headless=not args.headed,
        limit=args.limit,
    )

    ok = sum(1 for r in results if r["status"] == "ok")
    failed = [r for r in results if r["status"] == "failed"]
    ingested = sum(
        r.get("matches", {}).get("ingested", 0) for r in results if r["status"] == "ok"
    )
    print(f"\n=== daily: {ok}/{len(results)} leagues ok, {ingested} new matches ingested ===")
    for r in failed:
        print(f"  FAILED comp {r['job'].competition_id} {r['job'].season_label}: {r['error']}")
    # non-zero exit on any league failure so the cron surfaces it
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
