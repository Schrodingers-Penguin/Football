"""Unit tests for the xT tagger logic (synthetic grid — independent of the fit)."""

from src.stats.xt import (
    COLS,
    ROWS,
    cell_index,
    sum_action_value,
    xt_carry,
    xt_pass,
    xt_total,
)

# Synthetic grid where each cell's value == its flat index, so a move's value
# delta == end_index - start_index (easy to hand-check).
GRID = [float(i) for i in range(COLS * ROWS)]
P = 1


def test_cell_index_corners_and_clamp():
    assert cell_index(0, 0) == 0
    assert cell_index(100, 100) == COLS * ROWS - 1  # clamped into the grid
    assert cell_index(50, 50) == 8 * ROWS + 6
    assert cell_index(None, None) == 0


def test_sum_action_value_delta():
    # (10,50) -> col 1 row 6 = idx 18 ; (90,50) -> col 14 row 6 = idx 174
    assert cell_index(10, 50) == 18
    assert cell_index(90, 50) == 174
    assert sum_action_value([(10, 50, 90, 50)], GRID) == 156.0


def test_sum_action_value_backward_is_negative():
    assert sum_action_value([(90, 50, 10, 50)], GRID) == -156.0


def _pass(x, y, end_x, end_y, outcome="Successful", quals=()):
    return {
        "player_id": P,
        "type_name": "Pass",
        "outcome_name": outcome,
        "x": x,
        "y": y,
        "qualifiers": [
            {"type": {"displayName": "PassEndX"}, "value": str(end_x)},
            {"type": {"displayName": "PassEndY"}, "value": str(end_y)},
            *[{"type": {"displayName": q}, "value": None} for q in quals],
        ],
    }


def test_xt_pass_sums_only_successful_open_play():
    events = [
        _pass(10, 50, 90, 50),  # +156
        _pass(10, 50, 90, 50, outcome="Unsuccessful"),  # excluded
        _pass(10, 50, 90, 50, quals=["CornerTaken"]),  # set piece excluded
    ]
    assert xt_pass(events, P, grid=GRID) == 156.0


def test_xt_total_is_pass_plus_carry():
    events = [_pass(10, 50, 90, 50)]
    assert xt_carry(events, P, grid=GRID) == 0.0  # no carries derivable here
    assert xt_total(events, P, grid=GRID) == xt_pass(events, P, grid=GRID)
