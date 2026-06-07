"""Carry-derived stat taggers."""

from ._qualifiers import get_qualifier

_PASS_OR_SHOT = {"Pass", "Goal", "SavedShot", "MissedShots", "ShotOnPost"}
_SET_PIECE_QUALIFIERS = {"GoalKick", "KeeperThrow", "ThrowIn", "CornerTaken", "FreekickTaken"}


def _is_set_piece(event: dict) -> bool:
    for q in event.get("qualifiers", []):
        if q["type"]["displayName"] in _SET_PIECE_QUALIFIERS:
            return True
    return False


def _pass_end_coords(event: dict) -> tuple[float, float] | None:
    ex = get_qualifier(event, "PassEndX")
    ey = get_qualifier(event, "PassEndY")
    if ex is None or ey is None:
        return None
    return float(ex), float(ey)


def _derive_carries(events: list[dict], player_id: int) -> list[tuple[float, float, float, float]]:
    """Derive (start_x, start_y, end_x, end_y) carries ending in a Pass/Shot.

    A carry runs from where the player *received/won* the ball to where they
    release it. The receipt is the **immediately preceding event in the global
    stream** — so any opponent touch in between breaks the carry (continuous
    possession only) — within the same period and ≤1 minute, and is one of:
      - the player's own prior on-ball event → carry starts at its location;
      - a completed pass from a team-mate (a reception) → carry starts at that
        pass's end location.
    Using the player's own *previous touch* regardless of what happened in
    between (the earlier heuristic) counted off-ball repositioning as carrying
    and produced 50m+ phantom "carries"; this is the corrected definition.
    """
    carries: list[tuple[float, float, float, float]] = []

    for gi, event in enumerate(events):
        if event["player_id"] != player_id:
            continue
        if event["type_name"] not in _PASS_OR_SHOT:
            continue
        if _is_set_piece(event) or gi == 0:
            continue

        prev = events[gi - 1]
        if _is_set_piece(prev):
            continue
        if prev.get("period") != event.get("period"):
            continue
        if (event.get("minute") or 0) - (prev.get("minute") or 0) > 1:
            continue

        if prev["player_id"] == player_id:
            sx, sy = prev.get("x"), prev.get("y")
        elif (
            prev["type_name"] == "Pass"
            and prev.get("outcome_name") == "Successful"
            and prev.get("team_id") == event.get("team_id")
        ):
            start = _pass_end_coords(prev)
            if start is None:
                continue
            sx, sy = start
        else:
            continue

        cx, cy = event.get("x"), event.get("y")
        if sx is None or sy is None or cx is None or cy is None:
            continue

        carries.append((float(sx), float(sy), float(cx), float(cy)))

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


# --- v2 metrics (SPEC §8.4) -------------------------------------------------

_FINAL_THIRD_X = 100 * 2 / 3
_PITCH_X_M = 105.0  # 0-100 x-axis maps onto a 105m pitch length
_PITCH_Y_M = 68.0  # 0-100 y-axis maps onto a 68m pitch width


def count_carries_into_final_third(events: list[dict], player_id: int) -> int:
    return sum(
        1
        for sx, _sy, ex, _ey in _derive_carries(events, player_id)
        if sx < _FINAL_THIRD_X <= ex
    )


def count_carries_into_box(events: list[dict], player_id: int) -> int:
    count = 0
    for sx, sy, ex, ey in _derive_carries(events, player_id):
        in_box = ex >= 83 and 21 <= ey <= 79
        start_in_box = sx >= 83 and 21 <= sy <= 79
        if in_box and not start_in_box:
            count += 1
    return count


def carry_distance_total(events: list[dict], player_id: int) -> float:
    """Total straight-line carry distance, metres."""
    total = 0.0
    for sx, sy, ex, ey in _derive_carries(events, player_id):
        dx = (ex - sx) / 100 * _PITCH_X_M
        dy = (ey - sy) / 100 * _PITCH_Y_M
        total += (dx * dx + dy * dy) ** 0.5
    return round(total, 2)


def carry_progressive_distance(events: list[dict], player_id: int) -> float:
    """Total toward-goal carry distance ('fields gained'), metres — forward only."""
    total = 0.0
    for sx, _sy, ex, _ey in _derive_carries(events, player_id):
        forward = ex - sx
        if forward > 0:
            total += forward / 100 * _PITCH_X_M
    return round(total, 2)
