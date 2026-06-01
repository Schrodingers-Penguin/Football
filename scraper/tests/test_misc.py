"""Unit tests for misc stat taggers."""

from src.stats.misc import count_ball_recoveries, count_fouls_drawn

PLAYER = 1
OTHER = 2


def _ev(type_name: str, player_id: int = PLAYER, outcome: str = "Successful") -> dict:
    return {
        "player_id": player_id,
        "type_name": type_name,
        "outcome_name": outcome,
        "qualifiers": [],
    }


def test_fouls_drawn_successful_only():
    events = [
        _ev("Foul"),
        _ev("Foul"),
        _ev("Foul", outcome="Unsuccessful"),
        _ev("Foul", player_id=OTHER),
    ]
    assert count_fouls_drawn(events, PLAYER) == 2


def test_fouls_drawn_zero():
    events = [_ev("Pass")]
    assert count_fouls_drawn(events, PLAYER) == 0


def test_ball_recoveries():
    events = [
        _ev("BallRecovery"),
        _ev("BallRecovery"),
        _ev("BallRecovery", player_id=OTHER),
        _ev("Pass"),
    ]
    assert count_ball_recoveries(events, PLAYER) == 2


def test_ball_recoveries_zero():
    events = [_ev("Pass")]
    assert count_ball_recoveries(events, PLAYER) == 0
