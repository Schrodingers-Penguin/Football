"""Progressive passes received stat tagger."""

from ._qualifiers import get_qualifier, has_qualifier

_TOLERANCE = 2.0


def _is_progressive_pass(event: dict) -> bool:
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


def count_progressive_passes_received(events: list[dict], player_id: int) -> int:
    """Count progressive passes received by this player.

    A progressive pass is 'received' if the next event by this player within
    5 events after the pass has coordinates within ±2 of the pass endpoint.
    """
    count = 0
    n = len(events)

    for i, event in enumerate(events):
        if not _is_progressive_pass(event):
            continue

        end_x_str = get_qualifier(event, "PassEndX")
        end_y_str = get_qualifier(event, "PassEndY")
        if end_x_str is None or end_y_str is None:
            continue

        end_x = float(end_x_str)
        end_y = float(end_y_str)

        for j in range(i + 1, min(i + 6, n)):
            next_ev = events[j]
            if next_ev["player_id"] != player_id:
                continue
            nx = next_ev.get("x")
            ny = next_ev.get("y")
            if nx is None or ny is None:
                continue
            if abs(nx - end_x) <= _TOLERANCE and abs(ny - end_y) <= _TOLERANCE:
                count += 1
                break

    return count
