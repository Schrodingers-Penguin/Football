"""Shot-Creating Action (SCA) and Goal-Creating Action (GCA) taggers."""


SHOT_TYPES = {"Goal", "SavedShot", "MissedShots", "ShotOnPost"}

_ELIGIBLE_TYPES = {"Pass", "TakeOn", "Foul", "BallRecovery", "Interception", "Tackle"}

_DEAD_BALL_QUALIFIERS = {"GoalKick", "KeeperThrow", "ThrowIn", "CornerTaken", "FreekickTaken"}


def _is_eligible_action(event: dict) -> bool:
    t = event["type_name"]
    if t not in _ELIGIBLE_TYPES:
        return False
    if t == "TakeOn" and event["outcome_name"] != "Successful":
        return False
    if t == "Foul" and event["outcome_name"] != "Successful":
        return False
    if t == "Tackle" and event["outcome_name"] != "Successful":
        return False
    return True


def _is_dead_ball_restart(event: dict) -> bool:
    for q in event.get("qualifiers", []):
        if q["type"]["displayName"] in _DEAD_BALL_QUALIFIERS:
            return True
    return False


def _collect_sca_credits(events: list[dict], shot_index: int) -> list[int]:
    """Return up to 2 player IDs credited for SCA leading to events[shot_index].

    Walks back from shot_index, skipping the shot itself, until two eligible
    actions are found or a dead-ball restart is hit.
    """
    credits: list[int] = []
    seen_players: set[int] = set()

    for i in range(shot_index - 1, -1, -1):
        if len(credits) >= 2:
            break

        ev = events[i]

        if _is_dead_ball_restart(ev):
            break

        if ev["type_name"] == "Goal":
            break

        if not _is_eligible_action(ev):
            continue

        pid = ev["player_id"]
        if pid is None:
            continue
        if pid in seen_players:
            continue

        seen_players.add(pid)
        credits.append(pid)

    return credits


def _count_creating_actions(events: list[dict], player_id: int, goals_only: bool) -> int:
    count = 0
    for i, ev in enumerate(events):
        if ev["type_name"] not in SHOT_TYPES:
            continue
        if goals_only and ev["type_name"] != "Goal":
            continue
        credits = _collect_sca_credits(events, i)
        if player_id in credits:
            count += 1
    return count


def count_sca(events: list[dict], player_id: int) -> int:
    """Shot-Creating Actions: credited for the 2 actions immediately before any shot."""
    return _count_creating_actions(events, player_id, goals_only=False)


def count_gca(events: list[dict], player_id: int) -> int:
    """Goal-Creating Actions: as SCA but only for shots resulting in a goal."""
    return _count_creating_actions(events, player_id, goals_only=True)
