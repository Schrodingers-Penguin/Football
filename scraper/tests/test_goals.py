"""Unit tests for goals stat taggers."""

from src.stats.goals import count_npg, count_shots

PLAYER = 1
OTHER = 2


def _make_event(type_name: str, player_id: int = PLAYER, qualifiers: list | None = None) -> dict:
    return {
        "player_id": player_id,
        "type_name": type_name,
        "outcome_name": "Successful",
        "qualifiers": qualifiers or [],
    }


def test_count_npg_basic():
    events = [
        _make_event("Goal"),
        _make_event("Goal"),
        _make_event("SavedShot"),
    ]
    assert count_npg(events, PLAYER) == 2


def test_count_npg_excludes_penalty():
    events = [
        _make_event("Goal"),
        _make_event("Goal", qualifiers=[{"type": {"displayName": "Penalty"}, "value": None}]),
    ]
    assert count_npg(events, PLAYER) == 1


def test_count_npg_excludes_other_player():
    events = [
        _make_event("Goal"),
        _make_event("Goal", player_id=OTHER),
    ]
    assert count_npg(events, PLAYER) == 1


def test_count_shots_all_types():
    events = [
        _make_event("Goal"),
        _make_event("SavedShot"),
        _make_event("MissedShots"),
        _make_event("ShotOnPost"),
    ]
    assert count_shots(events, PLAYER) == 4


def test_count_shots_excludes_penalty():
    events = [
        _make_event("Goal"),
        _make_event("SavedShot", qualifiers=[{"type": {"displayName": "Penalty"}, "value": None}]),
    ]
    assert count_shots(events, PLAYER) == 1


def test_count_shots_zero_when_no_shots():
    events = [_make_event("Pass")]
    assert count_shots(events, PLAYER) == 0
