"""Miscellaneous stat taggers."""


def count_fouls_drawn(events: list[dict], player_id: int) -> int:
    """Foul events by this player with Successful outcome (foul drawn = player was fouled).

    In WhoScored, a Foul event with Successful outcome belongs to the player who drew the foul.
    """
    return sum(
        1
        for e in events
        if e["player_id"] == player_id
        and e["type_name"] == "Foul"
        and e["outcome_name"] == "Successful"
    )


def count_ball_recoveries(events: list[dict], player_id: int) -> int:
    """BallRecovery events by this player."""
    return sum(
        1
        for e in events
        if e["player_id"] == player_id and e["type_name"] == "BallRecovery"
    )


# --- v2 metrics (SPEC §8.4) -------------------------------------------------


def count_miscontrols(events: list[dict], player_id: int) -> int:
    """Unsuccessful BallTouch events (a bad first touch / failed control)."""
    return sum(
        1
        for e in events
        if e["player_id"] == player_id
        and e["type_name"] == "BallTouch"
        and e["outcome_name"] == "Unsuccessful"
    )


def count_dispossessed(events: list[dict], player_id: int) -> int:
    """Dispossessed events (tackled/robbed in possession)."""
    return sum(
        1 for e in events if e["player_id"] == player_id and e["type_name"] == "Dispossessed"
    )
