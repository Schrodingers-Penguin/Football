"""Roll player_match_stats up into player_season_stats.

Run after a backfill to (re)compute season-level per-90s and percentiles inputs.
Idempotent — safe to re-run; overwrites existing season rows.

Examples:
  # one season by id
  python scripts/aggregate_season.py --season-id 1

  # one season by competition + label (resolves the id)
  python scripts/aggregate_season.py --competition 2 --season 2025-2026

  # every season in the DB
  python scripts/aggregate_season.py --all
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import get_client
from src.ingest.season_rollup import (
    refresh_dashboard_views,
    rollup_all_seasons,
    rollup_season,
)


def main() -> None:
    ap = argparse.ArgumentParser(description="Aggregate player_match_stats -> player_season_stats.")
    ap.add_argument("--season-id", type=int, help="seasons.id to roll up")
    ap.add_argument("--competition", type=int, help="WhoScored competition id (with --season)")
    ap.add_argument("--season", help="season label, e.g. 2025-2026 (with --competition)")
    ap.add_argument("--all", action="store_true", help="roll up every season in the DB")
    args = ap.parse_args()

    if args.all:
        summaries = rollup_all_seasons()
        print(f"\n{summaries}")
        refresh_dashboard_views()  # after the summary — this raises if a view is stale
        return

    season_id = args.season_id
    if season_id is None:
        if args.competition is None or args.season is None:
            ap.error("provide --season-id, or --competition and --season, or --all")
        client = get_client()
        res = (
            client.table("seasons")
            .select("id")
            .eq("competition_id", args.competition)
            .eq("season_label", args.season)
            .execute()
        )
        if not res.data:
            ap.error(f"no season row for competition={args.competition} season={args.season}")
        season_id = res.data[0]["id"]

    summary = rollup_season(season_id)
    refresh_dashboard_views()
    print(f"\n{summary}")


if __name__ == "__main__":
    main()
