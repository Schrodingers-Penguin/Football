"""Defensive stat taggers."""

from ._qualifiers import has_qualifier

_DEF_THIRD_X = 100 / 3
_ATT_THIRD_X = 100 * 2 / 3


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


# --- v2 metrics (SPEC §8.4) -------------------------------------------------


def count_tackles_won(events: list[dict], player_id: int) -> int:
    """Tackle events with Successful outcome."""
    return sum(
        1
        for e in events
        if e["player_id"] == player_id
        and e["type_name"] == "Tackle"
        and e["outcome_name"] == "Successful"
    )


def _tackles_in_zone(events: list[dict], player_id: int, lo: float, hi: float) -> int:
    return sum(
        1
        for e in events
        if e["player_id"] == player_id
        and e["type_name"] == "Tackle"
        and lo <= (e.get("x") or 0.0) < hi
    )


def count_tackles_def_third(events: list[dict], player_id: int) -> int:
    return _tackles_in_zone(events, player_id, 0.0, _DEF_THIRD_X)


def count_tackles_mid_third(events: list[dict], player_id: int) -> int:
    return _tackles_in_zone(events, player_id, _DEF_THIRD_X, _ATT_THIRD_X)


def count_tackles_att_third(events: list[dict], player_id: int) -> int:
    # inclusive upper bound so a tackle at x=100 counts
    return _tackles_in_zone(events, player_id, _ATT_THIRD_X, 100.0001)


def count_dribbled_past(events: list[dict], player_id: int) -> int:
    """Times the player was beaten by a take-on (Challenge event)."""
    return sum(
        1 for e in events if e["player_id"] == player_id and e["type_name"] == "Challenge"
    )


def count_errors_leading_to_shot(events: list[dict], player_id: int) -> int:
    """Error events that led to an opponent attempt (LeadingToAttempt qualifier)."""
    return sum(
        1
        for e in events
        if e["player_id"] == player_id
        and e["type_name"] == "Error"
        and has_qualifier(e, "LeadingToAttempt")
    )
