"""Shooting-quality stat taggers (SPEC §8.4).

Shots-on-target %, npxG/shot and G−xG reuse columns already produced in
match aggregation (shots_on_target, shots, npxg, npg) and are derived at the
season level. These taggers cover the pieces that need the raw shot events:
average shot distance (stored as a summable distance total) and big chances.
"""

from ._qualifiers import has_qualifier
from .goals import SHOT_TYPES

_PITCH_X_M = 105.0
_PITCH_Y_M = 68.0
_GOAL = (100.0, 50.0)  # opponent goal centre on the 0-100 grid
_BOX_X, _BOX_Y_MIN, _BOX_Y_MAX = 83, 21, 79  # penalty-area bounding box
_LONG_RANGE_M = 25.0  # "long-distance" shot threshold


def _np_shots(events: list[dict], player_id: int) -> list[dict]:
    return [
        e
        for e in events
        if e["player_id"] == player_id
        and e["type_name"] in SHOT_TYPES
        and not has_qualifier(e, "Penalty")
    ]


def _shot_distance(e: dict) -> float:
    dx = (_GOAL[0] - (e.get("x") or 0.0)) / 100 * _PITCH_X_M
    dy = (_GOAL[1] - (e.get("y") or 0.0)) / 100 * _PITCH_Y_M
    return (dx * dx + dy * dy) ** 0.5


def _in_box(e: dict) -> bool:
    return (e.get("x") or 0.0) >= _BOX_X and _BOX_Y_MIN <= (e.get("y") or 0.0) <= _BOX_Y_MAX


def shot_distance_sum(events: list[dict], player_id: int) -> float:
    """Sum of distance (m) from each non-penalty shot to the goal centre.

    Stored summable so season average = sum / non-penalty shots.
    """
    return round(sum(_shot_distance(e) for e in _np_shots(events, player_id)), 2)


def count_shots_outside_box(events: list[dict], player_id: int) -> int:
    return sum(1 for e in _np_shots(events, player_id) if not _in_box(e))


def count_goals_outside_box(events: list[dict], player_id: int) -> int:
    return sum(
        1 for e in _np_shots(events, player_id) if e["type_name"] == "Goal" and not _in_box(e)
    )


def count_shots_long_range(events: list[dict], player_id: int) -> int:
    return sum(1 for e in _np_shots(events, player_id) if _shot_distance(e) >= _LONG_RANGE_M)


def count_goals_long_range(events: list[dict], player_id: int) -> int:
    return sum(
        1
        for e in _np_shots(events, player_id)
        if e["type_name"] == "Goal" and _shot_distance(e) >= _LONG_RANGE_M
    )


def _np_big_chance_shots(events: list[dict], player_id: int) -> list[dict]:
    return [e for e in _np_shots(events, player_id) if has_qualifier(e, "BigChance")]


def count_big_chances_faced(events: list[dict], player_id: int) -> int:
    """Non-penalty shots that were a big chance."""
    return len(_np_big_chance_shots(events, player_id))


def count_big_chances_scored(events: list[dict], player_id: int) -> int:
    """Big-chance shots that were scored."""
    return sum(1 for e in _np_big_chance_shots(events, player_id) if e["type_name"] == "Goal")
