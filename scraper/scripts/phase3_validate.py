"""Phase 3 validation: ingest Arsenal vs Fulham, print Saka's player_match_stats row."""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.aggregate.match import aggregate_match
from src.parser.events import parse_events
from src.understat.scraper import get_understat_xg

MATCH_DATA_PATH = Path(__file__).parent.parent / "phase1_match_data.json"
MATCH_ID = 1903405
COMPETITION_ID = 2
SEASON_LABEL = "2025-2026"
SAKA_ID = 367185


def main() -> None:
    print(f"Loading {MATCH_DATA_PATH}")
    match_data = json.loads(MATCH_DATA_PATH.read_text())

    raw_date = match_data.get("startDate", "")
    match_date = datetime.fromisoformat(raw_date).strftime("%Y-%m-%d")
    home_team = match_data["home"]["name"]
    away_team = match_data["away"]["name"]

    print(f"Match: {home_team} vs {away_team} on {match_date}")

    print("Fetching Understat xG data...")
    try:
        xg_data = get_understat_xg(
            competition_id=COMPETITION_ID,
            season_label=SEASON_LABEL,
            match_date=match_date,
            home_team=home_team,
            away_team=away_team,
        )
        if xg_data is None:
            print("Competition not on Understat — will use fallback model")
        else:
            print(f"Understat xG data: {len(xg_data)} players found")
    except Exception as exc:
        print(f"Understat fetch failed ({exc}) — falling back to xG model")
        xg_data = None

    print("Parsing events...")
    events = parse_events(match_data)
    print(f"  {len(events)} events parsed")

    print("Aggregating match stats...")
    rows = aggregate_match(
        events=events,
        match_data=match_data,
        xg_data=xg_data,
        match_id=MATCH_ID,
        competition_id=COMPETITION_ID,
        season_label=SEASON_LABEL,
    )
    print(f"  {len(rows)} player rows generated")

    saka_row = next((r for r in rows if r["player_id"] == SAKA_ID), None)
    if saka_row is None:
        print("ERROR: Saka not found in output rows")
        sys.exit(1)

    pid_map = match_data.get("playerIdNameDictionary", {})
    saka_name = pid_map.get(str(SAKA_ID), "Bukayo Saka")

    print(f"\n{'=' * 60}")
    print(f"  {saka_name} — player_match_stats")
    print(f"{'=' * 60}")
    col_width = 30
    for key, val in saka_row.items():
        print(f"  {key:<{col_width}} {val}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
