"""Unit tests for pure match-metadata extraction."""

from src.ingest.metadata import (
    extract_match_row,
    extract_players,
    extract_teams,
    map_status,
    parse_score,
)

MATCH = {
    "startDate": "2026-05-02T00:00:00",
    "startTime": "2026-05-02T17:30:00",
    "score": "3 : 0",
    "ftScore": "3 : 0",
    "statusCode": 6,
    "home": {
        "teamId": 13,
        "name": "Arsenal",
        "countryName": "England",
        "players": [
            {"playerId": 1, "name": "A", "height": 183},
            {"playerId": 2, "name": "B", "height": 0},
        ],
    },
    "away": {
        "teamId": 170,
        "name": "Fulham",
        "countryName": "England",
        "players": [
            {"playerId": 2, "name": "B", "height": 175},  # dup id across teams
            {"playerId": 3, "name": "C"},
        ],
    },
}


def test_parse_score():
    assert parse_score("3 : 0") == (3, 0)
    assert parse_score("2:1") == (2, 1)
    assert parse_score(None) == (None, None)
    assert parse_score("") == (None, None)
    assert parse_score("x : y") == (None, None)


def test_map_status():
    assert map_status(6) == "finished"
    assert map_status(1) == "scheduled"
    assert map_status(None) == "scheduled"


def test_extract_teams():
    teams = extract_teams(MATCH)
    assert {t["id"] for t in teams} == {13, 170}
    arsenal = next(t for t in teams if t["id"] == 13)
    assert arsenal["name"] == "Arsenal"
    assert arsenal["country"] == "England"
    assert arsenal["short_name"] is None


def test_extract_players_dedup_and_height():
    players = extract_players(MATCH)
    assert {p["id"] for p in players} == {1, 2, 3}  # id 2 deduped
    p1 = next(p for p in players if p["id"] == 1)
    assert p1["height_cm"] == 183
    p2 = next(p for p in players if p["id"] == 2)
    assert p2["height_cm"] is None  # height 0 -> null
    p3 = next(p for p in players if p["id"] == 3)
    assert p3["height_cm"] is None  # missing -> null


def test_extract_match_row():
    row = extract_match_row(MATCH, match_id=999, competition_id=2, season_id=7)
    assert row["id"] == 999
    assert row["competition_id"] == 2
    assert row["season_id"] == 7
    assert row["kickoff"] == "2026-05-02T17:30:00"  # startTime, not startDate
    assert row["home_team_id"] == 13
    assert row["away_team_id"] == 170
    assert row["home_score"] == 3
    assert row["away_score"] == 0
    assert row["status"] == "finished"
