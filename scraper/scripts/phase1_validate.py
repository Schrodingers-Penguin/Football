"""
Phase 1 validation.

Scrapes one WhoScored match, extracts events, prints:
  - Total event count
  - Breakdown of top event types
  - Saka's pass count (for user to cross-check against WhoScored UI)
  - Average pass start-x (coordinate orientation check)

Usage (from scraper/ directory with venv active):
    python scripts/phase1_validate.py <whoscored_match_url>

Saves the raw matchCentreData JSON to phase1_match_data.json for manual inspection.
"""

import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parser.events import parse_events
from whoscored.scraper import scrape_match


async def main(url: str) -> None:
    print(f"Scraping: {url}\n")
    match_data = await scrape_match(url)

    home = match_data.get("home", {})
    away = match_data.get("away", {})
    print(f"Match: {home.get('name')} vs {away.get('name')}")
    print(f"Match ID: {match_data.get('matchId')}")

    events = parse_events(match_data)
    print(f"Total events: {len(events)}")

    # Event type breakdown
    type_counts = Counter(e["type_name"] for e in events)
    print("\nTop event types:")
    for name, count in type_counts.most_common(15):
        print(f"  {name:<30} {count}")

    # --- Saka ---
    saka_events = [e for e in events if "saka" in e["player_name"].lower()]
    if not saka_events:
        print("\n⚠ No events found for a player named 'saka'.")
        print("  Players with events:")
        for name in sorted({e["player_name"] for e in events if e["player_name"]}):
            print(f"    {name}")
    else:
        player_name = saka_events[0]["player_name"]
        saka_passes = [e for e in saka_events if e["type_name"] == "Pass"]
        print(f"\n{player_name}:")
        print(f"  Total events: {len(saka_events)}")
        print(f"  Passes:       {len(saka_passes)}")

        # Coordinate orientation check
        passes_with_x = [p for p in saka_passes if p["x"] is not None]
        if passes_with_x:
            avg_x = sum(p["x"] for p in passes_with_x) / len(passes_with_x)
            print(f"  Avg pass start x: {avg_x:.1f}")
            print(
                f"  Coordinate check: {'✓ x > 50 (looks team-normalised)' if avg_x > 50 else '⚠ x <= 50 — verify orientation manually'}"
            )

    # Save raw JSON for manual inspection
    out = Path("phase1_match_data.json")
    out.write_text(json.dumps(match_data, indent=2))
    print(f"\nRaw matchCentreData saved → {out.resolve()}")
    print("\nNext step: compare 'Passes' count above against WhoScored's UI for this match.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <whoscored_match_url>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
