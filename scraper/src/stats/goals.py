"""Goal and shot stat taggers."""

from ._qualifiers import has_qualifier

SHOT_TYPES = {"Goal", "SavedShot", "MissedShots", "ShotOnPost"}


def count_npg(events: list[dict], player_id: int) -> int:
    """Non-penalty goals: Goal events by player excluding Penalty qualifier."""
    return sum(
        1
        for e in events
        if e["player_id"] == player_id
        and e["type_name"] == "Goal"
        and not has_qualifier(e, "Penalty")
    )


def count_shots(events: list[dict], player_id: int) -> int:
    """All shot events excluding penalties."""
    return sum(
        1
        for e in events
        if e["player_id"] == player_id
        and e["type_name"] in SHOT_TYPES
        and not has_qualifier(e, "Penalty")
    )
