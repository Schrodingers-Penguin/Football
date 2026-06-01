"""Unit tests for passing stat taggers."""

from src.stats.passing import (
    count_passes_attempted,
    count_passes_completed,
    count_progressive_passes,
)

PLAYER = 1
OTHER = 2


def _pass(
    player_id: int = PLAYER,
    outcome: str = "Successful",
    x: float = 50.0,
    end_x: float = 65.0,
    end_y: float = 50.0,
    qualifiers: list | None = None,
) -> dict:
    quals = qualifiers or []
    quals = [
        {"type": {"displayName": "PassEndX"}, "value": str(end_x)},
        {"type": {"displayName": "PassEndY"}, "value": str(end_y)},
    ] + quals
    return {
        "player_id": player_id,
        "type_name": "Pass",
        "outcome_name": outcome,
        "x": x,
        "y": 50.0,
        "qualifiers": quals,
    }


def _corner_qual() -> dict:
    return {"type": {"displayName": "CornerTaken"}, "value": None}


def test_passes_attempted_basic():
    events = [_pass(), _pass(outcome="Unsuccessful"), _pass(player_id=OTHER)]
    assert count_passes_attempted(events, PLAYER) == 2


def test_passes_attempted_excludes_corners():
    events = [_pass(), _pass(qualifiers=[_corner_qual()])]
    assert count_passes_attempted(events, PLAYER) == 1


def test_passes_completed_only_successful():
    events = [_pass(), _pass(outcome="Unsuccessful")]
    assert count_passes_completed(events, PLAYER) == 1


def test_passes_completed_excludes_corners():
    events = [_pass(), _pass(qualifiers=[_corner_qual()])]
    assert count_passes_completed(events, PLAYER) == 1


def test_progressive_passes_forward():
    # starts at x=50, ends at x=60 (10 yards forward >= 9.14)
    events = [_pass(x=50.0, end_x=60.0, end_y=50.0)]
    assert count_progressive_passes(events, PLAYER) == 1


def test_progressive_passes_into_pen_area():
    # ends in penalty area
    events = [_pass(x=50.0, end_x=85.0, end_y=50.0)]
    assert count_progressive_passes(events, PLAYER) == 1


def test_progressive_passes_excludes_defensive_40():
    # starts at x=30 (below 40)
    events = [_pass(x=30.0, end_x=42.0, end_y=50.0)]
    assert count_progressive_passes(events, PLAYER) == 0


def test_progressive_passes_excludes_corners():
    events = [_pass(x=50.0, end_x=62.0, end_y=50.0, qualifiers=[_corner_qual()])]
    assert count_progressive_passes(events, PLAYER) == 0


def test_progressive_passes_excludes_unsuccessful():
    events = [_pass(x=50.0, end_x=62.0, end_y=50.0, outcome="Unsuccessful")]
    assert count_progressive_passes(events, PLAYER) == 0


def test_progressive_passes_exactly_9_14_forward():
    # exactly 9.14 units forward from x=50 → end_x=59.14
    events = [_pass(x=50.0, end_x=59.14, end_y=50.0)]
    assert count_progressive_passes(events, PLAYER) == 1


def test_progressive_passes_just_below_threshold():
    # 9.13 < 9.14, and not in pen area, and not pen area end
    events = [_pass(x=50.0, end_x=59.13, end_y=50.0)]
    assert count_progressive_passes(events, PLAYER) == 0
