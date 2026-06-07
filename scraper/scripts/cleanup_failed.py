"""Retry the handful of matches that failed during the big backfill.

Failed matches never produced a `matches` row (ingest is all-or-nothing), so we
can't find them from the DB — we recover their ids from the backfill log files,
attributing each to the competition+season whose section it failed under. Then
we re-scrape via the slug-less /matches/<id>/live URL (no fixture re-discovery,
minimal WhoScored contact); backfill() skips any that have since been ingested.
Finally we re-roll-up every affected season.

Usage:
  python scripts/cleanup_failed.py LOG [LOG ...] [--delay 20] [--jitter 15]
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import get_client
from src.ingest.backfill import Fixture, backfill
from src.ingest.season_rollup import rollup_season
from src.ingest.writers import get_or_create_season

_BASE = "https://www.whoscored.com"
_HEADER = re.compile(r"\bcomp (\d+) (\d{4}-\d{4}) === start ===")
_FAIL = re.compile(r"\bFAIL (\d+):")


def parse_failures(log_paths: list[str]) -> dict[int, tuple[int, str]]:
    """match_id -> (competition_id, season_label), from the logs."""
    out: dict[int, tuple[int, str]] = {}
    for path in log_paths:
        comp_season: tuple[int, str] | None = None
        for line in Path(path).read_text().splitlines():
            h = _HEADER.search(line)
            if h:
                comp_season = (int(h.group(1)), h.group(2))
                continue
            f = _FAIL.search(line)
            if f and comp_season:
                out.setdefault(int(f.group(1)), comp_season)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Retry failed backfill matches from log files.")
    ap.add_argument("logs", nargs="+", help="backfill log file(s)")
    ap.add_argument("--delay", type=float, default=20.0)
    ap.add_argument("--jitter", type=float, default=15.0)
    args = ap.parse_args()

    failures = parse_failures(args.logs)
    print(f"{len(failures)} distinct failed match ids found in logs")

    fixtures = [
        Fixture(
            match_id=mid,
            url=f"{_BASE}/matches/{mid}/live",
            competition_id=comp,
            season_label=season,
        )
        for mid, (comp, season) in sorted(failures.items())
    ]

    summary = backfill(fixtures, delay_seconds=args.delay, jitter_seconds=args.jitter)
    print(f"\nretry: {summary}")

    # Re-roll-up every season we touched (recompute from the now-fuller stats).
    client = get_client()
    affected = sorted({cs for cs in failures.values()})
    for comp, season in affected:
        sid = get_or_create_season(client, comp, season)
        roll = rollup_season(sid, client=client)
        print(f"rollup comp {comp} {season}: {roll}")


if __name__ == "__main__":
    main()
