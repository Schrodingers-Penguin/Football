"""xG model: a logistic model fit offline against Understat's xG, applied at
runtime to WhoScored shot features only.

The coefficients live in the generated module ``xg_coefficients`` (produced by
``scripts/train_production_xg.py``). At runtime nothing from Understat is touched
— only WhoScored-derived features feed ``shot_xg``.

``build_features`` is the single source of truth for the feature vector and is
imported by BOTH the trainer and the runtime, so train/serve features cannot
drift apart.
"""

import math
from functools import lru_cache

# canonical feature order — trainer and runtime both rely on this exact layout
FEATURE_NAMES = [
    "distance",
    "distance_sq",
    "angle",
    "angle_sq",
    "dist_angle",
    "is_head",
    "sit_corner",
    "sit_setpiece",
    "sit_dfk",
    "la_throughball",
    "la_cross",
    "la_chipped",
    "la_headpass",
]
CONTINUOUS_IDX = (0, 1, 2, 3, 4)  # geometry terms that get standardized

SITUATIONS = ("open", "corner", "setpiece", "dfk")
LAST_ACTIONS = ("pass", "throughball", "cross", "chipped", "headpass")


def distance_angle(x100: float, y100: float) -> tuple[float, float]:
    """Shot distance (m) and visible-goal angle (rad) from 0-100 pitch coords.

    Goal centre at x=100 (105m), posts at y≈44.8 and y≈55.2 (30.5m, 37.5m).
    Angle is symmetric in y about the centre, so y-orientation is irrelevant.
    """
    x_m, y_m = x100 * 1.05, y100 * 0.68
    dx = 105.0 - x_m
    distance = math.hypot(dx, 34.0 - y_m)
    d1 = math.hypot(dx, y_m - 30.5)
    d2 = math.hypot(dx, y_m - 37.5)
    cos_a = (d1 * d1 + d2 * d2 - 49.0) / (2 * d1 * d2) if d1 and d2 else 1.0
    return distance, math.acos(max(-1.0, min(1.0, cos_a)))


def build_features(
    x100: float,
    y100: float,
    is_head: bool,
    situation: str = "open",
    last_action: str = "pass",
) -> list[float]:
    """Feature vector for one non-penalty shot. ``situation`` ∈ SITUATIONS,
    ``last_action`` ∈ LAST_ACTIONS."""
    d, a = distance_angle(x100, y100)
    return [
        d,
        d * d,
        a,
        a * a,
        d * a,
        1.0 if is_head else 0.0,
        1.0 if situation == "corner" else 0.0,
        1.0 if situation == "setpiece" else 0.0,
        1.0 if situation == "dfk" else 0.0,
        1.0 if last_action == "throughball" else 0.0,
        1.0 if last_action == "cross" else 0.0,
        1.0 if last_action == "chipped" else 0.0,
        1.0 if last_action == "headpass" else 0.0,
    ]


@lru_cache(maxsize=1)
def _coeffs():
    from . import xg_coefficients as c

    return c.MEANS, c.STDS, c.WEIGHTS, c.BIAS


def apply_coefficients(features: list[float]) -> float:
    """Apply the fitted logistic coefficients to a feature vector."""
    means, stds, weights, bias = _coeffs()
    z = bias
    for j, w in enumerate(weights):
        v = features[j]
        if j in CONTINUOUS_IDX:
            v = (v - means[j]) / stds[j]
        z += w * v
    if z < -35:
        return 1e-15
    if z > 35:
        return 1 - 1e-15
    return 1.0 / (1.0 + math.exp(-z))


def shot_xg(
    x100: float,
    y100: float,
    is_head: bool = False,
    situation: str = "open",
    last_action: str = "pass",
) -> float:
    """Non-penalty xG for a shot from WhoScored-derived features."""
    return apply_coefficients(build_features(x100, y100, is_head, situation, last_action))
