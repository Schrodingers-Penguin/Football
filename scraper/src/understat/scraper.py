"""Fetch xG data from Understat for a given match."""

import difflib

import httpx

LEAGUE_MAP: dict[int, str | None] = {
    2: "EPL",
    4: "La_liga",
    3: "Bundesliga",
    5: "Serie_A",
    22: "Ligue_1",
    13: None,
    21: None,
    12: None,
}


def _season_year(season_label: str) -> str:
    """Convert '2025-2026' to '2025'."""
    return season_label.split("-")[0]


def _fuzzy_match(name: str, candidates: list[str], cutoff: float = 0.6) -> str | None:
    matches = difflib.get_close_matches(name, candidates, n=1, cutoff=cutoff)
    return matches[0] if matches else None


def _fetch_league_fixtures(league: str, season_year: str) -> list[dict]:
    url = f"https://understat.com/getLeagueData/{league}/{season_year}"
    headers = {"X-Requested-With": "XMLHttpRequest"}
    resp = httpx.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("dates", [])


def _fetch_match_data(understat_match_id: str) -> dict:
    url = f"https://understat.com/getMatchData/{understat_match_id}"
    headers = {"X-Requested-With": "XMLHttpRequest"}
    resp = httpx.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_understat_xg(
    competition_id: int,
    season_label: str,
    match_date: str,
    home_team: str,
    away_team: str,
) -> dict[str, dict] | None:
    """Return player_name -> {'npxg': float, 'xa': float} for all players in the match.

    Returns None if competition not on Understat.
    Raises ValueError if match not found.
    """
    league = LEAGUE_MAP.get(competition_id)
    if league is None:
        return None

    season_year = _season_year(season_label)
    fixtures = _fetch_league_fixtures(league, season_year)

    finished = [f for f in fixtures if f.get("isResult")]
    if not finished:
        raise ValueError(f"No finished fixtures found for {league} {season_year}")

    understat_teams = list({f["h"]["title"] for f in finished} | {f["a"]["title"] for f in finished})

    matched_home = _fuzzy_match(home_team, understat_teams)
    matched_away = _fuzzy_match(away_team, understat_teams)

    if matched_home is None:
        raise ValueError(f"Could not fuzzy-match home team '{home_team}' in Understat {league} {season_year}")
    if matched_away is None:
        raise ValueError(f"Could not fuzzy-match away team '{away_team}' in Understat {league} {season_year}")

    date_prefix = match_date[:10]
    candidates = [
        f for f in finished
        if f["h"]["title"] == matched_home and f["a"]["title"] == matched_away
    ]
    if not candidates:
        candidates = [
            f for f in finished
            if f["h"]["title"] == matched_home and f["a"]["title"] == matched_away
        ]

    if not candidates:
        raise ValueError(
            f"No Understat match found for {matched_home} vs {matched_away} in {league} {season_year}"
        )

    if len(candidates) > 1:
        date_candidates = [f for f in candidates if f.get("datetime", "").startswith(date_prefix)]
        if date_candidates:
            candidates = date_candidates

    fixture = candidates[0]
    match_id = fixture["id"]

    match_data = _fetch_match_data(match_id)
    shots_h = match_data.get("shots", {}).get("h", [])
    shots_a = match_data.get("shots", {}).get("a", [])

    result: dict[str, dict] = {}

    for shot in shots_h + shots_a:
        player_name = shot.get("player", "")
        if not player_name:
            continue
        xg = float(shot.get("xG", 0) or 0)
        situation = shot.get("situation", "")
        is_penalty = situation == "Penalty"
        assisted_by = shot.get("player_assisted") or None

        if player_name not in result:
            result[player_name] = {"npxg": 0.0, "xa": 0.0}
        if not is_penalty:
            result[player_name]["npxg"] += xg

        if assisted_by:
            if assisted_by not in result:
                result[assisted_by] = {"npxg": 0.0, "xa": 0.0}
            result[assisted_by]["xa"] += xg

    return result
