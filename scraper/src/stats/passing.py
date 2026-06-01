"""Passing stat taggers."""

from ._qualifiers import get_qualifier, has_qualifier


def count_passes_attempted(events: list[dict], player_id: int) -> int:
    """All pass events excluding corners taken."""
    return sum(
        1
        for e in events
        if e["player_id"] == player_id
        and e["type_name"] == "Pass"
        and not has_qualifier(e, "CornerTaken")
    )


def count_passes_completed(events: list[dict], player_id: int) -> int:
    """Successful pass events excluding corners taken."""
    return sum(
        1
        for e in events
        if e["player_id"] == player_id
        and e["type_name"] == "Pass"
        and e["outcome_name"] == "Successful"
        and not has_qualifier(e, "CornerTaken")
    )


def _is_progressive_pass(event: dict) -> bool:
    """Return True if a pass event is progressive (completed, from own half, moves ball forward)."""
    if event["type_name"] != "Pass":
        return False
    if event["outcome_name"] != "Successful":
        return False
    if has_qualifier(event, "CornerTaken"):
        return False

    start_x = event.get("x") or 0.0
    if start_x < 40:
        return False

    end_x_str = get_qualifier(event, "PassEndX")
    end_y_str = get_qualifier(event, "PassEndY")
    if end_x_str is None or end_y_str is None:
        return False

    end_x = float(end_x_str)
    end_y = float(end_y_str)

    forward_progress = end_x - start_x >= 9.14
    into_pen_area = end_x >= 83 and 21 <= end_y <= 79

    return forward_progress or into_pen_area


def count_progressive_passes(events: list[dict], player_id: int) -> int:
    """Completed passes meeting progressive criteria, excluding defensive 40% and corners."""
    return sum(
        1
        for e in events
        if e["player_id"] == player_id and _is_progressive_pass(e)
    )
