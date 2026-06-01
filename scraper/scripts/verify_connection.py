"""
Phase 0 validation: confirms Supabase connectivity and schema is applied.
Run from the scraper directory: python scripts/verify_connection.py
"""

import sys
from pathlib import Path

# Allow running without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from db import get_client


def main() -> None:
    client = get_client()

    # 1. Check all expected tables exist
    expected_tables = {
        "competitions", "seasons", "teams", "players", "matches",
        "player_match_stats", "player_season_stats", "percentile_config",
    }
    result = client.rpc("exec_sql", {"query": "SELECT 1"})  # dummy — real check below

    # Query information_schema via PostgREST isn't possible directly,
    # so we test by selecting from each table (0 rows is fine)
    missing = []
    for table in sorted(expected_tables):
        try:
            client.table(table).select("*", count="exact").limit(0).execute()
            print(f"  ✓ {table}")
        except Exception as e:
            print(f"  ✗ {table}: {e}")
            missing.append(table)

    if missing:
        print(f"\nFAILED: {len(missing)} table(s) missing: {missing}")
        sys.exit(1)

    # 2. Check competition seed data
    comps = client.table("competitions").select("id, name").order("id").execute()
    print(f"\nCompetitions ({len(comps.data)} rows):")
    for c in comps.data:
        print(f"  id={c['id']:>4}  {c['name']}")

    expected_comp_ids = {2, 4, 3, 5, 22, 13, 21, 12}
    actual_ids = {c["id"] for c in comps.data}
    if actual_ids != expected_comp_ids:
        print(f"\nFAILED: competition IDs mismatch")
        print(f"  expected: {sorted(expected_comp_ids)}")
        print(f"  actual:   {sorted(actual_ids)}")
        sys.exit(1)

    print("\nPhase 0 validation: PASSED")


if __name__ == "__main__":
    main()
