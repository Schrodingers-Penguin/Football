"""Unit tests for the xG/xA shot-context tagger.

Exact xG floats depend on the fitted coefficients, so where a value is
model-dependent we assert structure/attribution and 0 < xg < 1 rather than a
magic number. Situation and last-action mapping are deterministic and checked
against hand-built qualifier sets.
"""

from src.stats.shot_context import (
    compute_xg_xa,
    last_action,
    shot_situation,
)

SHOOTER = 10
PASSER = 11
TEAM = 100


def _q(*names: str, related: int | None = None) -> list[dict]:
    quals = [{"type": {"displayName": n}} for n in names]
    if related is not None:
        quals.append({"type": {"displayName": "RelatedEventId"}, "value": str(related)})
    return quals


def _shot(qualifiers, player_id=SHOOTER, team_id=TEAM, x=88.0, y=50.0, type_name="SavedShot"):
    return {
        "type_name": type_name,
        "player_id": player_id,
        "team_id": team_id,
        "event_id": 500,
        "x": x,
        "y": y,
        "qualifiers": qualifiers,
    }


def _pass(qualifiers, player_id=PASSER, team_id=TEAM, event_id=42):
    return {
        "type_name": "Pass",
        "player_id": player_id,
        "team_id": team_id,
        "event_id": event_id,
        "x": 70.0,
        "y": 40.0,
        "qualifiers": qualifiers,
    }


# ---- situation mapping (deterministic) ----
def test_shot_situation_mapping():
    assert shot_situation({"Penalty"}) == "penalty"
    assert shot_situation({"DirectFreekick"}) == "dfk"
    assert shot_situation({"FromCorner"}) == "corner"
    assert shot_situation({"SetPiece"}) == "setpiece"
    assert shot_situation({"ThrowinSetPiece"}) == "setpiece"
    assert shot_situation({"RegularPlay"}) == "open"
    assert shot_situation(set()) == "open"


def test_shot_situation_penalty_precedence():
    # Penalty wins even if other tags are present.
    assert shot_situation({"Penalty", "SetPiece"}) == "penalty"


# ---- last-action mapping (deterministic) ----
def test_last_action_mapping():
    assert last_action({"type_name": "Pass", "qualifiers": _q("Throughball")}) == "throughball"
    assert last_action({"type_name": "Pass", "qualifiers": _q("Cross")}) == "cross"
    assert last_action({"type_name": "Pass", "qualifiers": _q("Chipped")}) == "chipped"
    assert last_action({"type_name": "Pass", "qualifiers": _q("HeadPass")}) == "headpass"
    assert last_action({"type_name": "Pass", "qualifiers": _q("KeyPass")}) == "pass"
    assert last_action(None) == "pass"


# ---- attribution ----
def test_assisted_shot_credits_shooter_and_passer():
    events = [
        _pass(_q("KeyPass"), event_id=42),
        _shot(_q("RegularPlay", related=42)),
    ]
    npxg, xa = compute_xg_xa(events)
    assert SHOOTER in npxg and 0.0 < npxg[SHOOTER] < 1.0
    # passer's xA equals the xG of the shot their pass created
    assert xa[PASSER] == npxg[SHOOTER]


def test_unassisted_shot_has_no_xa():
    events = [_shot(_q("RegularPlay"))]  # no RelatedEventId
    npxg, xa = compute_xg_xa(events)
    assert SHOOTER in npxg
    assert xa == {}


def test_penalty_excluded_from_npxg_and_xa():
    events = [
        _pass(_q("KeyPass"), event_id=42),
        _shot(_q("Penalty", related=42), x=88.5, y=50.0),
    ]
    npxg, xa = compute_xg_xa(events)
    assert npxg == {}
    assert xa == {}


def test_assist_lookup_is_team_scoped():
    # A same eventId on the *other* team must not be picked up as the assist.
    events = [
        _pass(_q("KeyPass"), team_id=999, event_id=42),  # wrong team
        _shot(_q("RegularPlay", related=42)),
    ]
    npxg, xa = compute_xg_xa(events)
    assert SHOOTER in npxg
    assert xa == {}  # no same-team assist resolves


def test_header_lowers_xg_vs_foot_same_location():
    foot = [_shot(_q("RegularPlay"))]
    head = [
        _shot(
            _q(
                "RegularPlay",
            )
            + [{"type": {"displayName": "Head"}}]
        )
    ]
    npxg_foot, _ = compute_xg_xa(foot)
    npxg_head, _ = compute_xg_xa(head)
    assert npxg_head[SHOOTER] < npxg_foot[SHOOTER]
