"""Phase 3 validation: ingest Arsenal vs Fulham end-to-end (WhoScored only),
print Saka's player_match_stats row. xG/xA come from the fitted model — no
external data source."""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.aggregate.match import aggregate_match
from src.parser.events import parse_events

MATCH_DATA_PATH = Path(__file__).parent.parent / "phase1_match_data.json"
MATCH_ID = 1903405
COMPETITION_ID = 2
SEASON_LABEL = "2025-2026"
SAKA_ID = 367185


def main() -> None:
    print(f"Loading {MATCH_DATA_PATH}")
    match_data = json.loads(MATCH_DATA_PATH.read_text())

    match_date = datetime.fromisoformat(match_data.get("startDate", "")).strftime("%Y-%m-%d")
    print(f"Match: {match_data['home']['name']} vs {match_data['away']['name']} on {match_date}")

    print("Parsing events...")
    events = parse_events(match_data)
    print(f"  {len(events)} events parsed")

    print("Aggregating match stats (model xG/xA)...")
    rows = aggregate_match(
        events=events,
        match_data=match_data,
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
    for key, val in saka_row.items():
        print(f"  {key:<30} {val}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
