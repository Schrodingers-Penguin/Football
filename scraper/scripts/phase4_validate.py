"""Phase 4 single-match validation: ingest Arsenal vs Fulham end-to-end into
Supabase (Postgres + Storage), then read back to prove it landed.

Requires scraper/.env.local with SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY.

Usage (from scraper/):  python scripts/phase4_validate.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import get_client
from src.ingest.pipeline import ingest_match
from src.storage import download_raw_match

MATCH_DATA_PATH = Path(__file__).parent.parent / "phase1_match_data.json"
MATCH_ID = 1903405
COMPETITION_ID = 2
SEASON_LABEL = "2025-2026"
SAKA_ID = 367185


def main() -> None:
    match_data = json.loads(MATCH_DATA_PATH.read_text())
    client = get_client()

    print("Ingesting (force=True to re-run cleanly)...")
    result = ingest_match(
        match_data, COMPETITION_ID, SEASON_LABEL, MATCH_ID, client=client, force=True
    )
    print(f"  {result}")

    # 1. Read Saka's row back from Postgres
    res = (
        client.table("player_match_stats")
        .select("*")
        .eq("match_id", MATCH_ID)
        .eq("player_id", SAKA_ID)
        .execute()
    )
    assert res.data, "Saka row not found in player_match_stats"
    saka = res.data[0]
    print(f"\n{'=' * 60}\n  Bukayo Saka — player_match_stats (from Supabase)\n{'=' * 60}")
    for k in (
        "minutes",
        "position_played",
        "position_bucket",
        "goals",
        "assists",
        "npg",
        "npxg",
        "xa",
        "npxg_plus_xa",
        "shots",
        "sca",
        "gca",
    ):
        print(f"  {k:<22} {saka[k]}")
    print("=" * 60)

    # 2. Confirm match row + raw JSON in Storage
    m = (
        client.table("matches")
        .select("status,home_score,away_score,raw_json_path,ingested_at")
        .eq("id", MATCH_ID)
        .execute()
        .data[0]
    )
    print(
        f"\nmatch row: {m['home_score']}-{m['away_score']} {m['status']}, "
        f"ingested_at={m['ingested_at']}"
    )
    restored = download_raw_match(m["raw_json_path"], client=client)
    print(f"storage round-trip OK: {len(restored.get('events', []))} events in stored JSON")

    # 3. Counts
    n_players = (
        client.table("player_match_stats")
        .select("id", count="exact")
        .eq("match_id", MATCH_ID)
        .execute()
        .count
    )
    print(f"player_match_stats rows for match: {n_players}")
    print("\nPhase 4 single-match validation: PASSED")


if __name__ == "__main__":
    main()
