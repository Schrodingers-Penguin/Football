"""Parse WhoScored matchCentreData into a flat event list."""


def parse_events(match_data: dict) -> list[dict]:
    """Flatten matchCentreData events into normalised dicts.

    Each event dict contains the fields most useful for stat tagging.
    Raw qualifiers are preserved as-is for downstream processing.
    """
    players_by_id: dict[int, str] = {}
    team_side: dict[int, str] = {}  # team_id -> 'home' | 'away'

    for side in ("home", "away"):
        team = match_data.get(side, {})
        tid = team.get("teamId")
        if tid:
            team_side[tid] = side
        for p in team.get("players", []):
            players_by_id[p["playerId"]] = p["name"]

    events: list[dict] = []
    for ev in match_data.get("events", []):
        player_id = ev.get("playerId")
        team_id = ev.get("teamId")
        events.append(
            {
                "id": ev.get("id"),
                "minute": ev.get("minute"),
                "second": ev.get("second", 0),
                "expanded_minute": ev.get("expandedMinute"),
                "period": ev.get("period", {}).get("value"),
                "team_id": team_id,
                "team_side": team_side.get(team_id, ""),
                "player_id": player_id,
                "player_name": players_by_id.get(player_id, ""),
                "type_id": ev.get("type", {}).get("value"),
                "type_name": ev.get("type", {}).get("displayName", ""),
                "outcome_id": ev.get("outcomeType", {}).get("value"),
                "outcome_name": ev.get("outcomeType", {}).get("displayName", ""),
                "x": ev.get("x"),
                "y": ev.get("y"),
                "end_x": ev.get("endX"),
                "end_y": ev.get("endY"),
                "qualifiers": ev.get("qualifiers", []),
                "is_touch": ev.get("isTouch", False),
            }
        )

    return events
