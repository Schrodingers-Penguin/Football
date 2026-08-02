"""Unit tests for player age recovery from matchCentreData (no DB)."""

from src.ingest.ages import ages_in_match, resolve_ages


def _match(*players, side="home"):
    return {side: {"players": list(players)}}


def test_reads_age_per_player():
    m = _match({"playerId": 1, "age": 24}, {"playerId": 2, "age": 31})
    assert ages_in_match(m, "2026-06-04") == [(1, "2026-06-04", 24), (2, "2026-06-04", 31)]


def test_reads_both_sides():
    m = {
        "home": {"players": [{"playerId": 1, "age": 24}]},
        "away": {"players": [{"playerId": 2, "age": 25}]},
    }
    assert {r[0] for r in ages_in_match(m, "2026-06-04")} == {1, 2}


def test_skips_missing_and_implausible_ages():
    m = _match(
        {"playerId": 1},  # no age
        {"playerId": 2, "age": None},
        {"playerId": 3, "age": 0},  # placeholder, not a real age
        {"playerId": 4, "age": 99},
        {"playerId": 5, "age": "24"},  # string, not int
        {"playerId": None, "age": 24},
        {"playerId": 7, "age": 24},  # the only good row
    )
    assert ages_in_match(m, "2026-06-04") == [(7, "2026-06-04", 24)]


def test_accepts_range_boundaries():
    m = _match({"playerId": 1, "age": 14}, {"playerId": 2, "age": 50})
    assert len(ages_in_match(m, "2026-06-04")) == 2


def test_empty_match():
    assert ages_in_match({}, "2026-06-04") == []


def test_resolve_takes_the_newest_observation():
    rows, stats = resolve_ages({"10": {"2026-06-02": 24, "2026-06-06": 24}})
    assert rows == [{"id": 10, "age": 24, "age_as_of": "2026-06-06"}]
    assert stats["single_age"] == 1


def test_resolve_uses_the_later_age_when_a_birthday_falls_in_the_window():
    # seen at 24 on the 2nd and 25 on the 6th -> birthday inside the window,
    # current age is 25
    rows, stats = resolve_ages({"10": {"2026-06-06": 25, "2026-06-02": 24}})
    assert rows == [{"id": 10, "age": 25, "age_as_of": "2026-06-06"}]
    assert stats["birthday_in_window"] == 1


def test_resolve_skips_players_with_no_observations():
    rows, stats = resolve_ages({"10": {}})
    assert rows == []
    assert stats["no_observations"] == 1


def test_resolve_empty():
    rows, stats = resolve_ages({})
    assert rows == []
    assert dict(stats) == {}
