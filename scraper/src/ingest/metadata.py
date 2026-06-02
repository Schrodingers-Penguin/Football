"""Pure extraction of normalized DB rows from matchCentreData.

No DB or network — just shapes matchCentreData into the rows the writers upsert.
Kept pure so it is fully unit-testable against a saved match JSON.
"""

# WhoScored statusCode -> our matches.status
_STATUS = {6: "finished"}


def map_status(status_code: int | None) -> str:
    return _STATUS.get(status_code, "scheduled")


def parse_score(score: str | None) -> tuple[int | None, int | None]:
    """'3 : 0' -> (3, 0). Returns (None, None) if unparseable."""
    if not score or ":" not in score:
        return None, None
    try:
        home, away = (part.strip() for part in score.split(":", 1))
        return int(home), int(away)
    except ValueError:
        return None, None


def extract_teams(match_data: dict) -> list[dict]:
    """One row per team: id, name, country (short_name not in matchCentreData)."""
    teams = []
    for side in ("home", "away"):
        t = match_data.get(side, {})
        if t.get("teamId") is None:
            continue
        teams.append(
            {
                "id": t["teamId"],
                "name": t.get("name", ""),
                "short_name": None,
                "country": t.get("countryName"),
            }
        )
    return teams


def extract_players(match_data: dict) -> list[dict]:
    """One row per player appearing in the match. matchCentreData only exposes
    height reliably; birth_date / nationality / preferred_foot stay null."""
    players: dict[int, dict] = {}
    for side in ("home", "away"):
        for p in match_data.get(side, {}).get("players", []):
            pid = p.get("playerId")
            if pid is None or pid in players:
                continue
            height = p.get("height")
            players[pid] = {
                "id": pid,
                "name": p.get("name", ""),
                "birth_date": None,
                "nationality": None,
                "preferred_foot": None,
                "height_cm": height if isinstance(height, int) and height > 0 else None,
            }
    return list(players.values())


def extract_match_row(
    match_data: dict,
    match_id: int,
    competition_id: int,
    season_id: int,
) -> dict:
    """The matches row. kickoff uses startTime (actual KO), not startDate (midnight)."""
    home_s, away_s = parse_score(match_data.get("ftScore") or match_data.get("score"))
    return {
        "id": match_id,
        "competition_id": competition_id,
        "season_id": season_id,
        "kickoff": match_data.get("startTime") or match_data.get("startDate"),
        "home_team_id": match_data.get("home", {}).get("teamId"),
        "away_team_id": match_data.get("away", {}).get("teamId"),
        "home_score": home_s,
        "away_score": away_s,
        "status": map_status(match_data.get("statusCode")),
    }
