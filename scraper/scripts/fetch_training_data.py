"""Pull multi-league shot data from Understat to fit the production xG model.

Self-contained (no runtime dependency on src/) — Understat is only ever touched
here, offline. The fitted coefficients get baked into src/stats/xg_coefficients.py,
after which the runtime pipeline is WhoScored-only.

Cached to one combined file; checkpoints after each league.
"""

import json
import time
from pathlib import Path

import httpx

LEAGUES = ["EPL", "La_liga", "Bundesliga", "Serie_A", "Ligue_1"]
SEASON = "2025"
OUT = Path(__file__).parent.parent / "xg_training_data.json"
_HEADERS = {"X-Requested-With": "XMLHttpRequest"}


def _fetch_league_fixtures(league: str, season_year: str) -> list[dict]:
    url = f"https://understat.com/getLeagueData/{league}/{season_year}"
    resp = httpx.get(url, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json().get("dates", [])


def _fetch_match_data(match_id: str) -> dict:
    url = f"https://understat.com/getMatchData/{match_id}"
    resp = httpx.get(url, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    all_shots: list[dict] = []
    for league in LEAGUES:
        fixtures = [f for f in _fetch_league_fixtures(league, SEASON) if f.get("isResult")]
        print(f"{league} {SEASON}: {len(fixtures)} matches")
        for i, fx in enumerate(fixtures):
            try:
                md = _fetch_match_data(fx["id"])
            except Exception as exc:
                print(f"  skip {fx['id']}: {exc}")
                continue
            for side in ("h", "a"):
                for s in md["shots"][side]:
                    all_shots.append(
                        {
                            "league": league,
                            "match_id": fx["id"],
                            "player": s.get("player", ""),
                            "X": float(s["X"]),
                            "Y": float(s["Y"]),
                            "xG": float(s["xG"]),
                            "result": s["result"],
                            "situation": s["situation"],
                            "shotType": s["shotType"],
                            "lastAction": s.get("lastAction", ""),
                        }
                    )
            if (i + 1) % 50 == 0:
                print(f"  {league}: {i+1}/{len(fixtures)}, {len(all_shots)} shots total")
            time.sleep(0.25)
        OUT.write_text(json.dumps(all_shots))
        print(f"  {league} done, {len(all_shots)} shots cached so far")

    print(f"\nwrote {len(all_shots)} shots -> {OUT.name}")


if __name__ == "__main__":
    main()
