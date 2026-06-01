"""Unit tests for carry-derived stat taggers."""

from src.stats.carries import count_progressive_carries, count_touches_att_pen_area

PLAYER = 1
OTHER = 2


def _event(
    player_id: int,
    type_name: str,
    x: float,
    y: float,
    minute: int = 10,
    period: int = 1,
    is_touch: bool = True,
    outcome: str = "Successful",
    qualifiers: list | None = None,
) -> dict:
    return {
        "player_id": player_id,
        "type_name": type_name,
        "outcome_name": outcome,
        "x": x,
        "y": y,
        "minute": minute,
        "period": period,
        "is_touch": is_touch,
        "qualifiers": qualifiers or [],
    }


def _pass(player_id: int = PLAYER, x: float = 50.0, y: float = 50.0, minute: int = 10, period: int = 1) -> dict:
    return _event(player_id, "Pass", x, y, minute=minute, period=period)


def _touch(player_id: int = PLAYER, x: float = 50.0, y: float = 50.0, minute: int = 10, period: int = 1) -> dict:
    return _event(player_id, "BallTouch", x, y, minute=minute, period=period, is_touch=True)


def test_progressive_carry_forward():
    # Player receives ball at x=50, then passes from x=62 (>= 9.14 forward carry)
    events = [
        _touch(x=50.0, y=50.0, minute=10),
        _pass(x=62.0, y=50.0, minute=10),
    ]
    assert count_progressive_carries(events, PLAYER) == 1


def test_progressive_carry_into_pen_area():
    # Player at x=80, next pass from x=85 in pen area
    events = [
        _touch(x=80.0, y=50.0, minute=10),
        _pass(x=85.0, y=50.0, minute=10),
    ]
    assert count_progressive_carries(events, PLAYER) == 1


def test_carry_excluded_from_defensive_40():
    # Starts at x=35 (below 40)
    events = [
        _touch(x=35.0, y=50.0, minute=10),
        _pass(x=47.0, y=50.0, minute=10),
    ]
    assert count_progressive_carries(events, PLAYER) == 0


def test_carry_excluded_large_time_gap():
    # Minutes diff > 3
    events = [
        _touch(x=50.0, y=50.0, minute=5),
        _pass(x=62.0, y=50.0, minute=10),
    ]
    assert count_progressive_carries(events, PLAYER) == 0


def test_carry_excluded_different_period():
    events = [
        _touch(x=50.0, y=50.0, minute=45, period=1),
        _pass(x=62.0, y=50.0, minute=45, period=2),
    ]
    assert count_progressive_carries(events, PLAYER) == 0


def test_carries_not_doubled_for_other_player():
    # Other player events don't count for PLAYER
    events = [
        _touch(OTHER, x=50.0, y=50.0, minute=10),
        _pass(PLAYER, x=62.0, y=50.0, minute=11),
    ]
    assert count_progressive_carries(events, PLAYER) == 0


def test_touches_att_pen_area_basic():
    events = [
        _event(PLAYER, "BallTouch", x=85.0, y=50.0, is_touch=True),
        _event(PLAYER, "BallTouch", x=90.0, y=30.0, is_touch=True),
        _event(PLAYER, "BallTouch", x=82.0, y=50.0, is_touch=True),  # x < 83, excluded
        _event(PLAYER, "BallTouch", x=85.0, y=20.0, is_touch=True),  # y < 21, excluded
        _event(PLAYER, "BallTouch", x=85.0, y=80.0, is_touch=True),  # y > 79, excluded
        _event(OTHER, "BallTouch", x=85.0, y=50.0, is_touch=True),   # other player
    ]
    assert count_touches_att_pen_area(events, PLAYER) == 2


def test_touches_att_pen_area_non_touch_excluded():
    events = [
        _event(PLAYER, "BallRecovery", x=85.0, y=50.0, is_touch=False),
    ]
    assert count_touches_att_pen_area(events, PLAYER) == 0
