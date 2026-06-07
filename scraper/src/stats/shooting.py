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


def _np_shots(events: list[dict], player_id: int) -> list[dict]:
    return [
        e
        for e in events
        if e["player_id"] == player_id
        and e["type_name"] in SHOT_TYPES
        and not has_qualifier(e, "Penalty")
    ]


def shot_distance_sum(events: list[dict], player_id: int) -> float:
    """Sum of distance (m) from each non-penalty shot to the goal centre.

    Stored summable so season average = sum / non-penalty shots.
    """
    total = 0.0
    for e in _np_shots(events, player_id):
        dx = (_GOAL[0] - (e.get("x") or 0.0)) / 100 * _PITCH_X_M
        dy = (_GOAL[1] - (e.get("y") or 0.0)) / 100 * _PITCH_Y_M
        total += (dx * dx + dy * dy) ** 0.5
    return round(total, 2)


def _np_big_chance_shots(events: list[dict], player_id: int) -> list[dict]:
    return [e for e in _np_shots(events, player_id) if has_qualifier(e, "BigChance")]


def count_big_chances_faced(events: list[dict], player_id: int) -> int:
    """Non-penalty shots that were a big chance."""
    return len(_np_big_chance_shots(events, player_id))


def count_big_chances_scored(events: list[dict], player_id: int) -> int:
    """Big-chance shots that were scored."""
    return sum(1 for e in _np_big_chance_shots(events, player_id) if e["type_name"] == "Goal")
