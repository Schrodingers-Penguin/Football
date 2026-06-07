"""Unit tests for possession segmentation and xGChain/xGBuildup."""

from src.stats.xgchain import compute_xg_chain, segment_possessions

A, B = 10, 20  # team ids


def ev(type_name, team, player, *, is_touch=True, eid=None, quals=None, x=80.0, y=50.0):
    return {
        "id": eid if eid is not None else id(object()),
        "event_id": eid,
        "type_name": type_name,
        "team_id": team,
        "player_id": player,
        "is_touch": is_touch,
        "outcome_name": "Successful",
        "x": x,
        "y": y,
        "qualifiers": quals or [],
    }


def test_possession_ends_on_shot_and_team_change():
    evs = [
        ev("Pass", A, 1),
        ev("Pass", A, 2),
        ev("MissedShots", A, 3),  # ends possession 1
        ev("Pass", B, 4),  # possession 2 (other team)
    ]
    poss = segment_possessions(evs)
    assert len(poss) == 2
    assert poss[0][0] == A and len(poss[0][1]) == 3
    assert poss[1][0] == B


def test_brief_opponent_interruption_does_not_split():
    # A passes, B gets a deflecting BlockedPass, A regains and shoots -> one chain
    evs = [
        ev("Pass", A, 1),
        ev("BlockedPass", B, 99),  # interruption; A regains next
        ev("Pass", A, 2),
        ev("Goal", A, 3),
    ]
    poss = segment_possessions(evs)
    # single A possession ending in the goal (B's touch ignored)
    assert len(poss) == 1
    team, run = poss[0]
    assert team == A
    assert {e["player_id"] for e in run if e["team_id"] == A} == {1, 2, 3}


def test_xg_chain_credits_all_involved_buildup_excludes_shooter_and_assister():
    # A possession: player1 -> player2 (assist, RelatedEventId link) -> player3 shoots
    assist = ev("Pass", A, 2, eid=500, x=70.0, y=50.0)
    assist["qualifiers"] = [
        {"type": {"displayName": "PassEndX"}, "value": "88"},
        {"type": {"displayName": "PassEndY"}, "value": "50"},
    ]
    shot = ev("SavedShot", A, 3, eid=501, x=88.0, y=50.0)
    shot["qualifiers"] = [{"type": {"displayName": "RelatedEventId"}, "value": "500"}]
    evs = [ev("Pass", A, 1, eid=499), assist, shot]

    chain, buildup = compute_xg_chain(evs)
    v = chain[1]
    assert v > 0
    # all three involved get the same chain value
    assert chain[1] == chain[2] == chain[3] == v
    # buildup excludes shooter (3) and assister (2); only player 1 keeps it
    assert buildup.get(1) == v
    assert 2 not in buildup and 3 not in buildup


def test_possession_without_shot_credits_nothing():
    evs = [ev("Pass", A, 1), ev("Pass", A, 2)]
    chain, buildup = compute_xg_chain(evs)
    assert chain == {} and buildup == {}
