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


# --- v2 metrics (SPEC §8.4) -------------------------------------------------

FINAL_THIRD_X = 100 * 2 / 3  # attacking third boundary on the 0-100 x-axis
_PASS_SET_PIECE = {"CornerTaken", "FreekickTaken", "IndirectFreekickTaken", "ThrowIn", "GoalKick"}


def _is_set_piece_pass(event: dict) -> bool:
    return any(q["type"]["displayName"] in _PASS_SET_PIECE for q in event.get("qualifiers", []))


def _pass_end(event: dict) -> tuple[float, float] | None:
    ex = get_qualifier(event, "PassEndX")
    ey = get_qualifier(event, "PassEndY")
    if ex is None or ey is None:
        return None
    return float(ex), float(ey)


def _is_pass(event: dict, player_id: int) -> bool:
    return event["player_id"] == player_id and event["type_name"] == "Pass"


def count_key_passes(events: list[dict], player_id: int) -> int:
    """Passes that directly lead to a shot (KeyPass qualifier); superset of assists."""
    return sum(1 for e in events if _is_pass(e, player_id) and has_qualifier(e, "KeyPass"))


def count_through_balls_attempted(events: list[dict], player_id: int) -> int:
    return sum(1 for e in events if _is_pass(e, player_id) and has_qualifier(e, "Throughball"))


def count_through_balls_completed(events: list[dict], player_id: int) -> int:
    return sum(
        1
        for e in events
        if _is_pass(e, player_id)
        and e["outcome_name"] == "Successful"
        and has_qualifier(e, "Throughball")
    )


def count_crosses_attempted(events: list[dict], player_id: int) -> int:
    """Open-play crosses (Cross qualifier, excluding set-piece deliveries)."""
    return sum(
        1
        for e in events
        if _is_pass(e, player_id) and has_qualifier(e, "Cross") and not _is_set_piece_pass(e)
    )


def count_crosses_completed(events: list[dict], player_id: int) -> int:
    return sum(
        1
        for e in events
        if _is_pass(e, player_id)
        and e["outcome_name"] == "Successful"
        and has_qualifier(e, "Cross")
        and not _is_set_piece_pass(e)
    )


def count_passes_into_final_third(events: list[dict], player_id: int) -> int:
    """Completed open-play passes that move the ball into the attacking third."""
    count = 0
    for e in events:
        if not _is_pass(e, player_id) or e["outcome_name"] != "Successful":
            continue
        if _is_set_piece_pass(e):
            continue
        start_x = e.get("x")
        end = _pass_end(e)
        if start_x is None or end is None:
            continue
        if start_x < FINAL_THIRD_X <= end[0]:
            count += 1
    return count


def count_passes_into_box(events: list[dict], player_id: int) -> int:
    """Completed open-play passes into the penalty area from a start outside it."""
    count = 0
    for e in events:
        if not _is_pass(e, player_id) or e["outcome_name"] != "Successful":
            continue
        if _is_set_piece_pass(e):
            continue
        start_x, start_y = e.get("x"), e.get("y")
        end = _pass_end(e)
        if start_x is None or start_y is None or end is None:
            continue
        end_x, end_y = end
        in_box = end_x >= 83 and 21 <= end_y <= 79
        start_in_box = start_x >= 83 and 21 <= start_y <= 79
        if in_box and not start_in_box:
            count += 1
    return count


def count_long_balls_attempted(events: list[dict], player_id: int) -> int:
    return sum(
        1
        for e in events
        if _is_pass(e, player_id)
        and has_qualifier(e, "Longball")
        and not has_qualifier(e, "CornerTaken")
    )


def count_long_balls_completed(events: list[dict], player_id: int) -> int:
    return sum(
        1
        for e in events
        if _is_pass(e, player_id)
        and e["outcome_name"] == "Successful"
        and has_qualifier(e, "Longball")
        and not has_qualifier(e, "CornerTaken")
    )


def count_big_chances_created(events: list[dict], player_id: int) -> int:
    return sum(1 for e in events if _is_pass(e, player_id) and has_qualifier(e, "BigChanceCreated"))
