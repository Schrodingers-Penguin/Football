"""Assist stat tagger."""

from ._qualifiers import has_qualifier


def count_assists(events: list[dict], player_id: int) -> int:
    """Pass events by player with IntentionalGoalAssist qualifier."""
    return sum(
        1
        for e in events
        if e["player_id"] == player_id
        and e["type_name"] == "Pass"
        and has_qualifier(e, "IntentionalGoalAssist")
    )
