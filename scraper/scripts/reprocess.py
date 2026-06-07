"""Reprocess stored match JSONs through the current taggers (no re-scrape).

Back-populates new/changed metric columns onto already-ingested matches by
re-aggregating the verbatim JSON in Supabase Storage, then re-rolls-up the
affected seasons. Idempotent.

Examples:
  # one season (resolve its id first with verify_connection / SQL), 5 matches
  python scripts/reprocess.py --season-id 1 --limit 5

  # a whole competition
  python scripts/reprocess.py --competition 2

  # everything (the full ~7k-match back-population)
  python scripts/reprocess.py
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingest.reprocess import reprocess_all


def main() -> None:
    ap = argparse.ArgumentParser(description="Reprocess stored matches through current taggers.")
    ap.add_argument("--competition", type=int, default=None, help="limit to a competition id")
    ap.add_argument("--season-id", type=int, default=None, help="limit to a seasons.id")
    ap.add_argument("--limit", type=int, default=None, help="cap number of matches")
    ap.add_argument("--no-rollup", action="store_true", help="skip the season re-rollup")
    args = ap.parse_args()

    summary = reprocess_all(
        competition_id=args.competition,
        season_id=args.season_id,
        limit=args.limit,
        rollup=not args.no_rollup,
    )
    print(f"\n{summary}")


if __name__ == "__main__":
    main()
