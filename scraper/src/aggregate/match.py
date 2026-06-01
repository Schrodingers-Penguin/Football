"""Aggregate match events into player_match_stats rows."""

from ..parser.events import parse_events
from ..stats._qualifiers import has_qualifier
from ..stats.assists import count_assists
from ..stats.carries import count_progressive_carries, count_touches_att_pen_area
from ..stats.defending import (
    count_aerials_total,
    count_aerials_won,
    count_clearances,
    count_interceptions,
    count_tackles,
)
from ..stats.goals import count_npg, count_shots
from ..stats.misc import count_ball_recoveries, count_fouls_drawn
from ..stats.passing import (
    count_passes_attempted,
    count_passes_completed,
    count_progressive_passes,
)
from ..stats.progressive_received import count_progressive_passes_received
from ..stats.sca import count_gca, count_sca
from ..stats.take_ons import count_successful_take_ons, count_take_ons_attempted
from ..stats.xg_model import estimate_xg

_POSITION_BUCKET: dict[str, str] = {
    "GK": "GK",
    "DC": "CB",
    "DL": "FB",
    "DR": "FB",
    "DMC": "DM",
    "DML": "DM",
    "DMR": "DM",
    "MC": "CM",
    "ML": "CM",
    "MR": "CM",
    "AMC": "AM",
    "AML": "W",
    "AMR": "W",
    "FW": "CF",
    "FWL": "CF",
    "FWR": "CF",
}

_SHOT_TYPES = {"Goal", "SavedShot", "MissedShots", "ShotOnPost"}


def _shots_on_target(events: list[dict], player_id: int) -> int:
    return sum(
        1
        for e in events
        if e["player_id"] == player_id
        and e["type_name"] in ("SavedShot", "Goal")
        and not has_qualifier(e, "Penalty")
    )


def _blocks(events: list[dict], player_id: int) -> int:
    return sum(
        1
        for e in events
        if e["player_id"] == player_id
        and e["type_name"] == "BlockedPass"
    )


def _compute_xg_from_model(events: list[dict], player_id: int) -> tuple[float, float]:
    """Compute (npxg, xa) from the fallback xG model."""
    npxg = 0.0
    xa = 0.0

    shot_events_by_id: dict[int, dict] = {}
    for ev in events:
        if ev["type_name"] in _SHOT_TYPES:
            shot_events_by_id[ev.get("id", 0)] = ev

    for ev in events:
        if ev["player_id"] != player_id:
            continue
        if ev["type_name"] not in _SHOT_TYPES:
            continue
        if has_qualifier(ev, "Penalty"):
            continue

        x = ev.get("x") or 0.0
        y = ev.get("y") or 0.0
        is_head = has_qualifier(ev, "Head")
        xg = estimate_xg(x, y, is_head, is_penalty=False)
        npxg += xg

    for ev in events:
        if ev["player_id"] != player_id:
            continue
        if ev["type_name"] != "Pass":
            continue
        if not has_qualifier(ev, "IntentionalGoalAssist"):
            continue

        related_shot: dict | None = None
        for shot_ev in shot_events_by_id.values():
            if shot_ev.get("player_id") != player_id:
                pass
            pass

        ev_id = ev.get("id")
        for shot_ev in events:
            if shot_ev["type_name"] not in _SHOT_TYPES:
                continue
            for q in shot_ev.get("qualifiers", []):
                if q["type"]["displayName"] == "RelatedEventId" and str(q.get("value")) == str(ev_id):
                    related_shot = shot_ev
                    break
            if related_shot:
                break

        if related_shot is not None:
            sx = related_shot.get("x") or 0.0
            sy = related_shot.get("y") or 0.0
            is_head = has_qualifier(related_shot, "Head")
            is_pen = has_qualifier(related_shot, "Penalty")
            xa += estimate_xg(sx, sy, is_head, is_pen)

    return npxg, xa


def _lookup_xg(
    player_name: str,
    xg_data: dict[str, dict] | None,
) -> tuple[float, float]:
    if xg_data is None:
        return 0.0, 0.0

    if player_name in xg_data:
        row = xg_data[player_name]
        return float(row.get("npxg", 0)), float(row.get("xa", 0))

    lower = player_name.lower()
    for k, v in xg_data.items():
        if k.lower() == lower:
            return float(v.get("npxg", 0)), float(v.get("xa", 0))

    return 0.0, 0.0


def aggregate_match(
    events: list[dict],
    match_data: dict,
    xg_data: dict[str, dict] | None,
    match_id: int,
    competition_id: int,
    season_label: str,
) -> list[dict]:
    """Return list of player_match_stats rows for all players with >0 minutes."""
    max_minute: int = match_data.get("maxMinute") or 90

    all_players: list[dict] = []
    for side in ("home", "away"):
        team = match_data.get(side, {})
        team_id = team.get("teamId")
        for p in team.get("players", []):
            all_players.append(
                {
                    **p,
                    "team_id": team_id,
                    "side": side,
                }
            )

    rows: list[dict] = []

    for p in all_players:
        player_id: int = p["playerId"]
        player_name: str = p.get("name", "")
        position: str = p.get("position") or "Sub"

        if position == "Sub" or position is None:
            if "subbedInExpandedMinute" not in p:
                continue
            sub_in = int(p["subbedInExpandedMinute"])
            minutes = max_minute - sub_in
            if minutes <= 0:
                continue
            position = "Sub"
            bucket = None
        else:
            if "subbedOutExpandedMinute" in p:
                minutes = int(p["subbedOutExpandedMinute"])
            else:
                minutes = max_minute

            bucket = _POSITION_BUCKET.get(position)

        if bucket is None and position != "Sub":
            bucket = None

        if xg_data is not None:
            npxg, xa = _lookup_xg(player_name, xg_data)
        else:
            npxg, xa = _compute_xg_from_model(events, player_id)

        npxg_plus_xa = npxg + xa

        row: dict = {
            "match_id": match_id,
            "player_id": player_id,
            "team_id": p["team_id"],
            "position_played": position,
            "position_bucket": bucket,
            "minutes": minutes,
            "goals": sum(
                1
                for e in events
                if e["player_id"] == player_id and e["type_name"] == "Goal"
            ),
            "assists": count_assists(events, player_id),
            "npg": count_npg(events, player_id),
            "npxg": round(npxg, 4),
            "xa": round(xa, 4),
            "npxg_plus_xa": round(npxg_plus_xa, 4),
            "shots": count_shots(events, player_id),
            "shots_on_target": _shots_on_target(events, player_id),
            "passes_attempted": count_passes_attempted(events, player_id),
            "passes_completed": count_passes_completed(events, player_id),
            "progressive_passes": count_progressive_passes(events, player_id),
            "progressive_passes_received": count_progressive_passes_received(events, player_id),
            "successful_take_ons": count_successful_take_ons(events, player_id),
            "take_ons_attempted": count_take_ons_attempted(events, player_id),
            "progressive_carries": count_progressive_carries(events, player_id),
            "touches_in_att_pen_area": count_touches_att_pen_area(events, player_id),
            "tackles": count_tackles(events, player_id),
            "interceptions": count_interceptions(events, player_id),
            "blocks": _blocks(events, player_id),
            "clearances": count_clearances(events, player_id),
            "aerials_won": count_aerials_won(events, player_id),
            "aerials_lost": count_aerials_total(events, player_id) - count_aerials_won(events, player_id),
            "fouls_drawn": count_fouls_drawn(events, player_id),
            "ball_recoveries": count_ball_recoveries(events, player_id),
            "sca": count_sca(events, player_id),
            "gca": count_gca(events, player_id),
        }

        rows.append(row)

    return rows
