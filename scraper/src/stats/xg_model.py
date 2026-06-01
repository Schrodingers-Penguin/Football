"""Fallback xG model for competitions not on Understat."""

import math


def estimate_xg(x_coord: float, y_coord: float, is_head: bool, is_penalty: bool) -> float:
    """Estimate xG for a shot from WhoScored coordinates.

    Coordinate conversion: x_m = x_coord * 1.05, y_m = y_coord * 0.68
    Goal center at x=100 (105m), y=50 (34m).
    Goal posts at y≈44.8 (30.5m) and y≈55.2 (37.5m).
    """
    x_m = x_coord * 1.05
    y_m = y_coord * 0.68

    goal_x_m = 105.0
    goal_y_m = 34.0
    post_y1_m = 30.5
    post_y2_m = 37.5

    dx = goal_x_m - x_m
    dy = goal_y_m - y_m
    distance = math.sqrt(dx * dx + dy * dy)

    d1 = math.sqrt(dx * dx + (y_m - post_y1_m) ** 2)
    d2 = math.sqrt(dx * dx + (y_m - post_y2_m) ** 2)
    goal_width = abs(post_y2_m - post_y1_m)
    cos_angle = (d1 * d1 + d2 * d2 - goal_width ** 2) / (2 * d1 * d2)
    cos_angle = max(-1.0, min(1.0, cos_angle))
    angle = math.acos(cos_angle)

    intercept = -1.526
    w_distance = -0.1154
    w_angle = 1.845
    w_head = -0.8689
    w_penalty = 3.5

    linear = (
        intercept
        + distance * w_distance
        + angle * w_angle
        + (1 if is_head else 0) * w_head
        + (1 if is_penalty else 0) * w_penalty
    )
    return 1.0 / (1.0 + math.exp(-linear))
