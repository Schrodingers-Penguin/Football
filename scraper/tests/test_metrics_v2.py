"""Unit tests for v2 metric taggers (SPEC §8.4), hand-checked event inputs."""

from src.stats.carries import (
    carry_distance_total,
    carry_progressive_distance,
    count_carries_into_box,
    count_carries_into_final_third,
)
from src.stats.defending import (
    count_dribbled_past,
    count_errors_leading_to_shot,
    count_tackles_att_third,
    count_tackles_def_third,
    count_tackles_mid_third,
    count_tackles_won,
)
from src.stats.misc import count_dispossessed, count_miscontrols
from src.stats.passing import (
    count_big_chances_created,
    count_crosses_attempted,
    count_crosses_completed,
    count_key_passes,
    count_long_balls_completed,
    count_passes_into_box,
    count_passes_into_final_third,
    count_through_balls_attempted,
)
from src.stats.shooting import (
    count_big_chances_faced,
    count_big_chances_scored,
    shot_distance_sum,
)
from src.stats.shot_context import compute_xg_xa

P = 1
OPP = 2


def q(*names):
    return [{"type": {"displayName": n}, "value": None} for n in names]


def pass_ev(player=P, outcome="Successful", x=50.0, y=50.0, end_x=60.0, end_y=50.0, quals=()):
    return {
        "player_id": player,
        "type_name": "Pass",
        "outcome_name": outcome,
        "x": x,
        "y": y,
        "period": 1,
        "minute": 10,
        "qualifiers": [
            {"type": {"displayName": "PassEndX"}, "value": str(end_x)},
            {"type": {"displayName": "PassEndY"}, "value": str(end_y)},
            *q(*quals),
        ],
    }


def ev(type_name, player=P, outcome="Successful", x=50.0, y=50.0, quals=()):
    return {
        "player_id": player,
        "type_name": type_name,
        "outcome_name": outcome,
        "x": x,
        "y": y,
        "period": 1,
        "minute": 10,
        "qualifiers": q(*quals),
    }


# --- passing / creation ----------------------------------------------------

def test_key_passes():
    assert count_key_passes([pass_ev(quals=["KeyPass"]), pass_ev()], P) == 1


def test_through_balls_attempted_counts_unsuccessful_too():
    evs = [pass_ev(quals=["Throughball"]), pass_ev(outcome="Unsuccessful", quals=["Throughball"])]
    assert count_through_balls_attempted(evs, P) == 2


def test_crosses_exclude_set_piece_and_completed_only_successful():
    evs = [
        pass_ev(quals=["Cross"]),  # open-play, completed
        pass_ev(outcome="Unsuccessful", quals=["Cross"]),  # attempted only
        pass_ev(quals=["Cross", "CornerTaken"]),  # set piece -> excluded
    ]
    assert count_crosses_attempted(evs, P) == 2
    assert count_crosses_completed(evs, P) == 1


def test_passes_into_final_third_crossing_boundary_only():
    into = pass_ev(x=60.0, end_x=70.0)  # 60 -> 70 crosses 66.67
    within = pass_ev(x=70.0, end_x=80.0)  # already in final third
    assert count_passes_into_final_third([into, within], P) == 1


def test_passes_into_box_from_outside():
    into = pass_ev(x=70.0, y=50.0, end_x=88.0, end_y=50.0)
    already = pass_ev(x=85.0, y=50.0, end_x=90.0, end_y=50.0)  # started in box
    assert count_passes_into_box([into, already], P) == 1


def test_long_balls_completed():
    evs = [pass_ev(quals=["Longball"]), pass_ev(outcome="Unsuccessful", quals=["Longball"])]
    assert count_long_balls_completed(evs, P) == 1


def test_big_chances_created():
    assert count_big_chances_created([pass_ev(quals=["BigChanceCreated"]), pass_ev()], P) == 1


# --- carrying --------------------------------------------------------------
# Carries are derived from a prev event -> a Pass/Shot by the same player.

def _carry_seq(sx, sy, ex, ey, player=P):
    # prev touch at (sx,sy), then a Pass at (ex,ey): a carry from prev->pass
    return [
        ev("BallTouch", player=player, x=sx, y=sy),
        pass_ev(player=player, x=ex, y=ey, end_x=ex, end_y=ey),
    ]


def test_carries_into_final_third():
    assert count_carries_into_final_third(_carry_seq(60, 50, 70, 50), P) == 1
    assert count_carries_into_final_third(_carry_seq(70, 50, 80, 50), P) == 0  # already in


def test_carries_into_box():
    assert count_carries_into_box(_carry_seq(70, 50, 88, 50), P) == 1


def test_carry_progressive_distance_forward_only_metres():
    # 50 -> 60 on x = 10/100 * 105 = 10.5 m forward
    assert carry_progressive_distance(_carry_seq(50, 50, 60, 50), P) == 10.5
    # backward carry contributes 0 to progressive distance
    assert carry_progressive_distance(_carry_seq(60, 50, 50, 50), P) == 0.0


def test_carry_distance_total_euclidean_metres():
    # 50->60 x (10.5m) and 50->50 y (0): distance 10.5
    assert carry_distance_total(_carry_seq(50, 50, 60, 50), P) == 10.5


# --- possession misc -------------------------------------------------------

def test_miscontrols_only_unsuccessful_balltouch():
    evs = [ev("BallTouch", outcome="Unsuccessful"), ev("BallTouch", outcome="Successful")]
    assert count_miscontrols(evs, P) == 1


def test_dispossessed():
    assert count_dispossessed([ev("Dispossessed"), ev("Pass")], P) == 1


# --- shooting --------------------------------------------------------------

def shot(type_name="MissedShots", player=P, x=88.0, y=50.0, quals=()):
    return ev(type_name, player=player, x=x, y=y, quals=quals)


def test_shot_distance_sum_excludes_penalty():
    # shot at x=88 -> (100-88)/100*105 = 12.6 m; penalty shot ignored
    evs = [shot(x=88.0, y=50.0), shot(x=88.0, y=50.0, quals=["Penalty"])]
    assert shot_distance_sum(evs, P) == 12.6


def test_distance_band_shots_and_goals():
    # in box (x=90), outside box (x=70 -> dist ~ (100-70)/100*105 = 31.5m, long range),
    # outside box but < 25m (x=80 -> dist 21m, not long range)
    evs = [
        shot("Goal", x=90.0, y=50.0),  # in box, scored
        shot("Goal", x=70.0, y=50.0),  # outside box, long range, scored
        shot("MissedShots", x=80.0, y=50.0),  # outside box, not long range
        shot("Goal", x=70.0, y=50.0, quals=["Penalty"]),  # excluded
    ]
    from src.stats.shooting import (
        count_goals_long_range,
        count_goals_outside_box,
        count_shots_long_range,
        count_shots_outside_box,
    )

    assert count_shots_outside_box(evs, P) == 2  # x=70 and x=80
    assert count_goals_outside_box(evs, P) == 1  # x=70 goal
    assert count_shots_long_range(evs, P) == 1  # only x=70 (31.5m)
    assert count_goals_long_range(evs, P) == 1


def test_big_chances_faced_and_scored():
    evs = [
        shot("Goal", quals=["BigChance"]),
        shot("MissedShots", quals=["BigChance"]),
        shot("Goal"),  # not a big chance
        shot("Goal", quals=["BigChance", "Penalty"]),  # penalty excluded
    ]
    assert count_big_chances_faced(evs, P) == 2
    assert count_big_chances_scored(evs, P) == 1


# --- defending -------------------------------------------------------------

def test_tackles_won_and_by_third():
    evs = [
        ev("Tackle", x=20.0),  # def third, successful
        ev("Tackle", x=50.0, outcome="Unsuccessful"),  # mid third
        ev("Tackle", x=90.0),  # att third
    ]
    assert count_tackles_won(evs, P) == 2
    assert count_tackles_def_third(evs, P) == 1
    assert count_tackles_mid_third(evs, P) == 1
    assert count_tackles_att_third(evs, P) == 1


def test_dribbled_past_and_errors():
    evs = [
        ev("Challenge", outcome="Unsuccessful"),
        ev("Error", quals=["LeadingToAttempt"]),
        ev("Error"),  # error not leading to a shot
    ]
    assert count_dribbled_past(evs, P) == 1
    assert count_errors_leading_to_shot(evs, P) == 1


# --- xA split --------------------------------------------------------------

def _shot_with_assist(assist_quals):
    # assist pass (event_id 100) by P, shot by OPP referencing it via RelatedEventId
    assist = {
        "player_id": P,
        "team_id": 9,
        "event_id": 100,
        "type_name": "Pass",
        "outcome_name": "Successful",
        "x": 70.0,
        "y": 50.0,
        "qualifiers": [
            {"type": {"displayName": "PassEndX"}, "value": "88"},
            {"type": {"displayName": "PassEndY"}, "value": "50"},
            *q(*assist_quals),
        ],
    }
    shot = {
        "player_id": OPP,
        "team_id": 9,
        "event_id": 101,
        "type_name": "MissedShots",
        "outcome_name": "Unsuccessful",
        "x": 88.0,
        "y": 50.0,
        "qualifiers": [{"type": {"displayName": "RelatedEventId"}, "value": "100"}],
    }
    return [assist, shot]


def test_xa_split_open_vs_set_piece_sums_to_total():
    npxg, xa, xa_op, xa_sp = compute_xg_xa(_shot_with_assist([]))
    assert xa.get(P, 0) > 0
    assert round(xa_op.get(P, 0), 6) == round(xa.get(P, 0), 6)
    assert xa_sp.get(P, 0) == 0

    npxg, xa, xa_op, xa_sp = compute_xg_xa(_shot_with_assist(["CornerTaken"]))
    assert round(xa_sp.get(P, 0), 6) == round(xa.get(P, 0), 6)
    assert xa_op.get(P, 0) == 0
