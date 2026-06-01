"""Unit tests for assists stat tagger."""

from src.stats.assists import count_assists

PLAYER = 1
OTHER = 2


def _pass(player_id: int = PLAYER, qualifiers: list | None = None) -> dict:
    return {
        "player_id": player_id,
        "type_name": "Pass",
        "outcome_name": "Successful",
        "qualifiers": qualifiers or [],
    }


def _intent_assist_qual() -> dict:
    return {"type": {"displayName": "IntentionalGoalAssist"}, "value": None}


def test_count_assists_basic():
    events = [
        _pass(qualifiers=[_intent_assist_qual()]),
        _pass(qualifiers=[_intent_assist_qual()]),
        _pass(),
    ]
    assert count_assists(events, PLAYER) == 2


def test_count_assists_other_player_not_counted():
    events = [
        _pass(qualifiers=[_intent_assist_qual()]),
        _pass(player_id=OTHER, qualifiers=[_intent_assist_qual()]),
    ]
    assert count_assists(events, PLAYER) == 1


def test_count_assists_non_pass_ignored():
    events = [
        {
            "player_id": PLAYER,
            "type_name": "Goal",
            "outcome_name": "Successful",
            "qualifiers": [_intent_assist_qual()],
        }
    ]
    assert count_assists(events, PLAYER) == 0


def test_count_assists_zero():
    events = [_pass()]
    assert count_assists(events, PLAYER) == 0
