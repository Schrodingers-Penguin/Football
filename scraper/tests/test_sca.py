"""Unit tests for SCA and GCA taggers."""

from src.stats.sca import count_gca, count_sca

PLAYER = 1
OTHER_A = 2
OTHER_B = 3


def _ev(
    type_name: str,
    player_id: int = PLAYER,
    outcome: str = "Successful",
    qualifiers: list | None = None,
) -> dict:
    return {
        "player_id": player_id,
        "type_name": type_name,
        "outcome_name": outcome,
        "qualifiers": qualifiers or [],
    }


def test_sca_pass_before_shot():
    events = [
        _ev("Pass", PLAYER),
        _ev("SavedShot", OTHER_A),
    ]
    assert count_sca(events, PLAYER) == 1


def test_sca_two_credits_for_same_shot():
    events = [
        _ev("Pass", PLAYER),
        _ev("Pass", OTHER_A),
        _ev("Goal", OTHER_B),
    ]
    assert count_sca(events, PLAYER) == 1
    assert count_sca(events, OTHER_A) == 1


def test_sca_same_player_only_once_per_shot():
    events = [
        _ev("Pass", PLAYER),
        _ev("Pass", PLAYER),
        _ev("SavedShot", OTHER_A),
    ]
    assert count_sca(events, PLAYER) == 1


def test_sca_stops_at_dead_ball():
    goalkick_qual = [{"type": {"displayName": "GoalKick"}, "value": None}]
    events = [
        _ev("Pass", PLAYER),
        _ev("Pass", OTHER_A, qualifiers=goalkick_qual),
        _ev("Pass", OTHER_B),
        _ev("SavedShot", OTHER_A),
    ]
    assert count_sca(events, PLAYER) == 0


def test_sca_takeon_must_be_successful():
    events = [
        _ev("TakeOn", PLAYER, outcome="Unsuccessful"),
        _ev("SavedShot", OTHER_A),
    ]
    assert count_sca(events, PLAYER) == 0


def test_sca_successful_takeon():
    events = [
        _ev("TakeOn", PLAYER, outcome="Successful"),
        _ev("SavedShot", OTHER_A),
    ]
    assert count_sca(events, PLAYER) == 1


def test_gca_only_goals():
    events = [
        _ev("Pass", PLAYER),
        _ev("SavedShot", OTHER_A),
        _ev("Pass", PLAYER),
        _ev("Goal", OTHER_A),
    ]
    assert count_gca(events, PLAYER) == 1
    assert count_sca(events, PLAYER) == 2


def test_gca_zero_no_goals():
    events = [
        _ev("Pass", PLAYER),
        _ev("SavedShot", OTHER_A),
    ]
    assert count_gca(events, PLAYER) == 0


def test_sca_multiple_shots():
    events = [
        _ev("Pass", PLAYER),
        _ev("SavedShot", OTHER_A),
        _ev("Pass", PLAYER),
        _ev("MissedShots", OTHER_B),
    ]
    assert count_sca(events, PLAYER) == 2
