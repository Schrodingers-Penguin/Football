"""xGChain / xGBuildup (SPEC §8.4.2).

Possession-involvement metrics. WhoScored carries no possession marker, so we
segment the event stream ourselves:

  - A possession is a run of one team's events.
  - It ends on a shot, a dead-ball restart, or the opponent establishing control.
  - Smoothing: a brief opponent interruption (block/clearance/interception/loose
    touch) that the same team regains on the very next on-ball event does NOT end
    the possession — without this, chains are severed by deflections and
    involvement collapses (~2 players/chain instead of the realistic ~3-4).

For every possession that ends in a shot, the possession value V = the highest
non-penalty model xG among its shots. Each player with an on-ball touch in that
possession is credited V once (xGChain); xGBuildup credits the same set minus the
shooter and the assister (the pass immediately before the shot).
"""

from .shot_context import iter_shot_xg

_SHOT_TYPES = {"Goal", "SavedShot", "MissedShots", "ShotOnPost"}

# Events that hard-end a possession (dead ball / stoppage / restart marker).
_HARD_END = {
    "Start",
    "End",
    "Card",
    "SubstitutionOn",
    "SubstitutionOff",
    "FormationChange",
    "FormationSet",
    "CornerAwarded",
    "Foul",
    "OffsideGiven",
    "OffsidePass",
    "OffsideProvoked",
}

# Opponent defensive touches that may be a brief interruption rather than a real
# turnover (only treated as interruption if the same team regains immediately).
_INTERRUPTION = {
    "BlockedPass",
    "Clearance",
    "Interception",
    "BallTouch",
    "Tackle",
    "Challenge",
    "BallRecovery",
    "Save",  # keeper stops the shot but the ball can rebound to the attacker
}


def _next_on_ball_team(events: list[dict], start: int) -> int | None:
    for e in events[start:]:
        if e.get("is_touch") and e.get("team_id") is not None:
            return e["team_id"]
    return None


def segment_possessions(events: list[dict]) -> list[tuple[int, list[dict]]]:
    """Split events into (team_id, events) possessions (see module docstring)."""
    possessions: list[tuple[int, list[dict]]] = []
    cur: list[dict] = []
    team: int | None = None

    for idx, e in enumerate(events):
        t = e["type_name"]
        et = e.get("team_id")

        if t in _HARD_END:
            if cur:
                possessions.append((team, cur))
            cur, team = [], None
            continue

        if team is None:
            team, cur = et, [e]
        elif et == team:
            cur.append(e)
        elif t in _INTERRUPTION and _next_on_ball_team(events, idx + 1) == team:
            continue  # brief opponent interruption, same team regains -> ignore
        else:
            possessions.append((team, cur))
            team, cur = et, [e]
        # Note: a shot does NOT end the possession — a saved/blocked shot that
        # rebounds to the same team stays one possession (rebounds credited once
        # at max xG). Possessions end on turnover or a _HARD_END restart.

    if cur:
        possessions.append((team, cur))
    return possessions


def compute_xg_chain(events: list[dict]) -> tuple[dict[int, float], dict[int, float]]:
    """Return (xg_chain, xg_buildup) by player for the match."""
    xg_by_id: dict[int, float] = {}
    assister_by_id: dict[int, int | None] = {}
    for ev, xg, _situation, assist in iter_shot_xg(events):
        xg_by_id[ev["id"]] = xg
        assister_by_id[ev["id"]] = assist["player_id"] if assist else None

    chain: dict[int, float] = {}
    buildup: dict[int, float] = {}

    for team, poss in segment_possessions(events):
        shots = [
            e
            for e in poss
            if e["type_name"] in _SHOT_TYPES and e["team_id"] == team and e["id"] in xg_by_id
        ]
        if not shots:
            continue
        best = max(shots, key=lambda s: xg_by_id[s["id"]])
        value = xg_by_id[best["id"]]
        shooter = best["player_id"]
        assister = assister_by_id.get(best["id"])

        involved = {
            e["player_id"]
            for e in poss
            if e["team_id"] == team and e.get("is_touch") and e.get("player_id") is not None
        }
        for p in involved:
            chain[p] = chain.get(p, 0.0) + value
            if p != shooter and p != assister:
                buildup[p] = buildup.get(p, 0.0) + value

    return chain, buildup
