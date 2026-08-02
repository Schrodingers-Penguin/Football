"""Recover player ages from stored raw match JSON.

matchCentreData reports each player's age at SCRAPE time, not at kickoff (a
2023 match ingested in June 2026 lists a player's June-2026 age). So the age is
paired with the match's ingested_at, never its kickoff, and the result is an
exact age on that date rather than a derived birth date.

Two phases so the expensive one is only paid once:

  --extract  download every stored match, write player_id -> {date: age} to a
             local JSON cache (~0.6 GB of Storage egress, a few minutes)
  --load     read the cache and write players.age / players.age_as_of

Examples:
  python scripts/backfill_ages.py --extract --out /tmp/ages.json
  python scripts/backfill_ages.py --load --out /tmp/ages.json
"""

import argparse
import json
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import get_client
from src.ingest.ages import ages_in_match, resolve_ages
from src.storage import download_raw_match

_PAGE = 1000
_WORKERS = 16


def _all_stored_matches(client) -> list[dict]:
    """Every match with raw JSON in Storage, with the date it was scraped."""
    rows: list[dict] = []
    start = 0
    while True:
        res = (
            client.table("matches")
            .select("id,raw_json_path,ingested_at")
            .not_.is_("raw_json_path", "null")
            .order("id")
            .range(start, start + _PAGE - 1)
            .execute()
        )
        batch = res.data or []
        rows.extend(batch)
        if len(batch) < _PAGE:
            break
        start += _PAGE
    return [r for r in rows if r.get("ingested_at")]


def _ages_in_match(client, match: dict) -> list[tuple[int, str, int]]:
    """(player_id, observed_date, age) for every player in one stored match."""
    data = download_raw_match(match["raw_json_path"], client=client)
    return ages_in_match(data, match["ingested_at"][:10])


def extract(out_path: Path, log=print) -> dict:
    client = get_client()
    matches = _all_stored_matches(client)
    log(f"{len(matches)} stored matches to read")

    obs: dict[int, dict[str, int]] = defaultdict(dict)
    done = failed = 0
    with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
        futures = {pool.submit(_ages_in_match, client, m): m["id"] for m in matches}
        for f in as_completed(futures):
            done += 1
            try:
                for pid, day, age in f.result():
                    obs[pid][day] = age
            except Exception as e:  # noqa: BLE001 — one bad blob shouldn't kill the run
                failed += 1
                if failed <= 5:
                    log(f"  match {futures[f]} failed: {e}")
            if done % 500 == 0:
                log(f"  {done}/{len(matches)} matches, {len(obs)} players so far")

    out_path.write_text(json.dumps({str(k): v for k, v in obs.items()}))
    log(f"wrote {len(obs)} players to {out_path} ({failed} matches failed)")
    return obs


def load(out_path: Path, log=print) -> None:
    client = get_client()
    obs = json.loads(out_path.read_text())
    rows, stats = resolve_ages(obs)
    log(f"{len(rows)} players resolved ({dict(stats)})")

    for i in range(0, len(rows), 500):
        client.table("players").upsert(rows[i : i + 500]).execute()
    log(f"wrote age for {len(rows)} players")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--extract", action="store_true", help="download raw JSON -> cache")
    ap.add_argument("--load", action="store_true", help="cache -> players.age")
    ap.add_argument("--out", type=Path, required=True, help="cache file path")
    args = ap.parse_args()

    if args.extract:
        extract(args.out)
    if args.load:
        load(args.out)
    if not (args.extract or args.load):
        ap.error("pass --extract and/or --load")


if __name__ == "__main__":
    main()
