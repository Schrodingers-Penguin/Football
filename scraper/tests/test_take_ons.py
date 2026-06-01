"""Unit tests for take-on stat taggers."""

from src.stats.take_ons import count_successful_take_ons, count_take_ons_attempted

PLAYER = 1
OTHER = 2


def _takeon(player_id: int = PLAYER, outcome: str = "Successful") -> dict:
    return {
        "player_id": player_id,
        "type_name": "TakeOn",
        "outcome_name": outcome,
        "qualifiers": [],
    }


def test_successful_take_ons_basic():
    events = [_takeon(), _takeon(outcome="Unsuccessful"), _takeon()]
    assert count_successful_take_ons(events, PLAYER) == 2


def test_successful_take_ons_excludes_other_player():
    events = [_takeon(), _takeon(player_id=OTHER)]
    assert count_successful_take_ons(events, PLAYER) == 1


def test_take_ons_attempted_all():
    events = [_takeon(), _takeon(outcome="Unsuccessful"), _takeon()]
    assert count_take_ons_attempted(events, PLAYER) == 3


def test_take_ons_attempted_zero():
    events = [{"player_id": PLAYER, "type_name": "Pass", "outcome_name": "Successful", "qualifiers": []}]
    assert count_take_ons_attempted(events, PLAYER) == 0


def test_take_ons_attempted_excludes_other_player():
    events = [_takeon(), _takeon(player_id=OTHER)]
    assert count_take_ons_attempted(events, PLAYER) == 1
