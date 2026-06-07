"""Derive xG-model features from WhoScored shot events, and compute per-player
non-penalty xG and xA for a match.

Feature derivation mirrors the trainer's mapping (see scripts/train_production_xg.py)
so train/serve features stay aligned:
  - situation:  WhoScored shot qualifiers -> open / corner / setpiece / dfk / penalty
  - last_action: assist pass (via RelatedEventId) -> throughball / cross / chipped / headpass / pass
  - is_head:    'Head' qualifier
"""

from .xg_model import shot_xg

_SHOT_TYPES = {"Goal", "SavedShot", "MissedShots", "ShotOnPost"}


def _names(event: dict) -> set[str]:
    return {q["type"]["displayName"] for q in event.get("qualifiers", [])}


def shot_situation(quals: set[str]) -> str:
    if "Penalty" in quals:
        return "penalty"
    if "DirectFreekick" in quals:
        return "dfk"
    if "FromCorner" in quals:
        return "corner"
    if "SetPiece" in quals or "ThrowinSetPiece" in quals:
        return "setpiece"
    return "open"


def _related_event_id(quals_list: list[dict]) -> int | None:
    for q in quals_list:
        if q["type"]["displayName"] == "RelatedEventId":
            val = q.get("value")
            if val is not None and str(val).lstrip("-").isdigit():
                return int(val)
    return None


def last_action(assist_event: dict | None) -> str:
    if assist_event is None:
        return "pass"
    quals = _names(assist_event)
    if "Throughball" in quals:
        return "throughball"
    if "Cross" in quals:
        return "cross"
    if "Chipped" in quals:
        return "chipped"
    if "HeadPass" in quals:
        return "headpass"
    return "pass"


# Assist-pass qualifiers that mark the key pass as a set-piece delivery.
_SET_PIECE_ASSIST = {
    "CornerTaken",
    "FreekickTaken",
    "IndirectFreekickTaken",
    "ThrowIn",
    "FromCorner",
    "SetPiece",
}


def _assist_is_set_piece(assist_event: dict) -> bool:
    return bool(_names(assist_event) & _SET_PIECE_ASSIST)


def iter_shot_xg(events: list[dict]):
    """Yield (shot_event, npxg, assist_event_or_None) for each non-penalty shot.

    Single source of truth for per-shot model xG and its key-pass attribution;
    consumed by both xA (compute_xg_xa) and the chain metrics (xGChain).
    """
    by_team_eid: dict[tuple, dict] = {}
    for e in events:
        eid = e.get("event_id")
        if eid is not None:
            by_team_eid.setdefault((e.get("team_id"), eid), e)

    for ev in events:
        if ev["type_name"] not in _SHOT_TYPES:
            continue
        quals = _names(ev)
        situation = shot_situation(quals)
        if situation == "penalty":
            continue  # npxG excludes penalties
        assist = by_team_eid.get((ev.get("team_id"), _related_event_id(ev.get("qualifiers", []))))
        xg = shot_xg(
            ev.get("x") or 0.0,
            ev.get("y") or 0.0,
            is_head="Head" in quals,
            situation=situation,
            last_action=last_action(assist),
        )
        yield ev, xg, assist


def compute_xg_xa(
    events: list[dict],
) -> tuple[dict[int, float], dict[int, float], dict[int, float], dict[int, float]]:
    """Return (npxg, xa, xa_open_play, xa_set_piece) by player for the match.

    npxG: sum of model xG over a player's non-penalty shots.
    xA:   sum of model xG of shots arising from a player's key passes
          (the shot's RelatedEventId pass; that passer is credited).
    xA is additionally split by whether that key pass was a set-piece delivery;
    xa_open_play + xa_set_piece == xa for every player.
    """
    npxg: dict[int, float] = {}
    xa: dict[int, float] = {}
    xa_open: dict[int, float] = {}
    xa_sp: dict[int, float] = {}

    for ev, xg, assist in iter_shot_xg(events):
        shooter = ev["player_id"]
        npxg[shooter] = npxg.get(shooter, 0.0) + xg

        if assist is not None and assist.get("player_id") is not None:
            passer = assist["player_id"]
            xa[passer] = xa.get(passer, 0.0) + xg
            bucket = xa_sp if _assist_is_set_piece(assist) else xa_open
            bucket[passer] = bucket.get(passer, 0.0) + xg

    return npxg, xa, xa_open, xa_sp
