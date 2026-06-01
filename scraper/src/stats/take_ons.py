"""Take-on stat taggers."""


def count_successful_take_ons(events: list[dict], player_id: int) -> int:
    """TakeOn events with Successful outcome."""
    return sum(
        1
        for e in events
        if e["player_id"] == player_id
        and e["type_name"] == "TakeOn"
        and e["outcome_name"] == "Successful"
    )


def count_take_ons_attempted(events: list[dict], player_id: int) -> int:
    """All TakeOn events regardless of outcome."""
    return sum(
        1
        for e in events
        if e["player_id"] == player_id
        and e["type_name"] == "TakeOn"
    )
