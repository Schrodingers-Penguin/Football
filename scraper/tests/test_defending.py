"""Unit tests for defending stat taggers."""

from src.stats.defending import (
    count_aerials_total,
    count_aerials_won,
    count_clearances,
    count_interceptions,
    count_tackles,
)

PLAYER = 1
OTHER = 2


def _ev(type_name: str, player_id: int = PLAYER, outcome: str = "Successful") -> dict:
    return {
        "player_id": player_id,
        "type_name": type_name,
        "outcome_name": outcome,
        "qualifiers": [],
    }


def test_tackles():
    events = [_ev("Tackle"), _ev("Tackle", outcome="Unsuccessful"), _ev("Tackle", player_id=OTHER)]
    assert count_tackles(events, PLAYER) == 2


def test_interceptions():
    events = [_ev("Interception"), _ev("Interception"), _ev("Interception", player_id=OTHER)]
    assert count_interceptions(events, PLAYER) == 2


def test_clearances():
    events = [_ev("Clearance"), _ev("Pass"), _ev("Clearance", player_id=OTHER)]
    assert count_clearances(events, PLAYER) == 1


def test_aerials_won():
    events = [
        _ev("Aerial"),
        _ev("Aerial"),
        _ev("Aerial", outcome="Unsuccessful"),
        _ev("Aerial", player_id=OTHER),
    ]
    assert count_aerials_won(events, PLAYER) == 2


def test_aerials_total():
    events = [
        _ev("Aerial"),
        _ev("Aerial", outcome="Unsuccessful"),
        _ev("Aerial", player_id=OTHER),
    ]
    assert count_aerials_total(events, PLAYER) == 2


def test_all_zero():
    events = [_ev("Pass")]
    assert count_tackles(events, PLAYER) == 0
    assert count_interceptions(events, PLAYER) == 0
    assert count_clearances(events, PLAYER) == 0
    assert count_aerials_won(events, PLAYER) == 0
    assert count_aerials_total(events, PLAYER) == 0
