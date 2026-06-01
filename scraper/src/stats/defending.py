"""Defensive stat taggers."""


def count_tackles(events: list[dict], player_id: int) -> int:
    """All Tackle events regardless of outcome."""
    return sum(
        1
        for e in events
        if e["player_id"] == player_id and e["type_name"] == "Tackle"
    )


def count_interceptions(events: list[dict], player_id: int) -> int:
    """All Interception events."""
    return sum(
        1
        for e in events
        if e["player_id"] == player_id and e["type_name"] == "Interception"
    )


def count_clearances(events: list[dict], player_id: int) -> int:
    """All Clearance events."""
    return sum(
        1
        for e in events
        if e["player_id"] == player_id and e["type_name"] == "Clearance"
    )


def count_aerials_won(events: list[dict], player_id: int) -> int:
    """Aerial events with Successful outcome."""
    return sum(
        1
        for e in events
        if e["player_id"] == player_id
        and e["type_name"] == "Aerial"
        and e["outcome_name"] == "Successful"
    )


def count_aerials_total(events: list[dict], player_id: int) -> int:
    """All Aerial events regardless of outcome."""
    return sum(
        1
        for e in events
        if e["player_id"] == player_id and e["type_name"] == "Aerial"
    )
