"""Carry-derived stat taggers."""

_PASS_OR_SHOT = {"Pass", "Goal", "SavedShot", "MissedShots", "ShotOnPost"}
_SET_PIECE_QUALIFIERS = {"GoalKick", "KeeperThrow", "ThrowIn", "CornerTaken", "FreekickTaken"}


def _is_set_piece(event: dict) -> bool:
    for q in event.get("qualifiers", []):
        if q["type"]["displayName"] in _SET_PIECE_QUALIFIERS:
            return True
    return False


def _derive_carries(events: list[dict], player_id: int) -> list[tuple[float, float, float, float]]:
    """Derive (start_x, start_y, end_x, end_y) carries for player_id.

    For each Pass or Shot event by the player, look back to find the immediately
    preceding event by the same player. The movement from that event's position
    to this event's position is a carry, subject to time/set-piece constraints.
    """
    carries: list[tuple[float, float, float, float]] = []

    player_events = [(i, e) for i, e in enumerate(events) if e["player_id"] == player_id]

    for idx_in_player, (global_idx, event) in enumerate(player_events):
        if event["type_name"] not in _PASS_OR_SHOT:
            continue
        if _is_set_piece(event):
            continue

        if idx_in_player == 0:
            continue

        _, prev = player_events[idx_in_player - 1]

        if prev["period"] != event["period"]:
            continue
        prev_min = prev.get("minute") or 0
        curr_min = event.get("minute") or 0
        if curr_min - prev_min > 3:
            continue
        if _is_set_piece(prev):
            continue

        px = prev.get("x")
        py = prev.get("y")
        cx = event.get("x")
        cy = event.get("y")
        if px is None or py is None or cx is None or cy is None:
            continue

        carries.append((float(px), float(py), float(cx), float(cy)))

    return carries


def count_progressive_carries(events: list[dict], player_id: int) -> int:
    """Carries meeting progressive criteria originating from own 60%."""
    count = 0
    for start_x, start_y, end_x, end_y in _derive_carries(events, player_id):
        if start_x < 40:
            continue
        forward_progress = end_x - start_x >= 9.14
        into_pen_area = end_x >= 83 and 21 <= end_y <= 79
        if forward_progress or into_pen_area:
            count += 1
    return count


def count_touches_att_pen_area(events: list[dict], player_id: int) -> int:
    """Touch events in the attacking penalty area (x >= 83, 21 <= y <= 79)."""
    return sum(
        1
        for e in events
        if e["player_id"] == player_id
        and e.get("is_touch")
        and (e.get("x") or 0) >= 83
        and 21 <= (e.get("y") or 0) <= 79
    )
