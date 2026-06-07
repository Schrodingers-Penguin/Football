"""Aggregate match events into player_match_stats rows."""

from ..stats._qualifiers import has_qualifier
from ..stats.assists import count_assists
from ..stats.carries import (
    carry_distance_total,
    carry_progressive_distance,
    count_carries_into_box,
    count_carries_into_final_third,
    count_progressive_carries,
    count_touches_att_pen_area,
)
from ..stats.defending import (
    count_aerials_total,
    count_aerials_won,
    count_clearances,
    count_dribbled_past,
    count_errors_leading_to_shot,
    count_interceptions,
    count_tackles,
    count_tackles_att_third,
    count_tackles_def_third,
    count_tackles_mid_third,
    count_tackles_won,
)
from ..stats.goals import count_npg, count_shots
from ..stats.misc import (
    count_ball_recoveries,
    count_dispossessed,
    count_fouls_drawn,
    count_miscontrols,
)
from ..stats.passing import (
    count_big_chances_created,
    count_crosses_attempted,
    count_crosses_completed,
    count_key_passes,
    count_long_balls_attempted,
    count_long_balls_completed,
    count_passes_attempted,
    count_passes_completed,
    count_passes_into_box,
    count_passes_into_final_third,
    count_progressive_passes,
    count_through_balls_attempted,
    count_through_balls_completed,
)
from ..stats.progressive_received import count_progressive_passes_received
from ..stats.sca import count_gca, count_sca
from ..stats.shooting import (
    count_big_chances_faced,
    count_big_chances_scored,
    shot_distance_sum,
)
from ..stats.shot_context import compute_xg_xa
from ..stats.take_ons import count_successful_take_ons, count_take_ons_attempted

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
    return sum(1 for e in events if e["player_id"] == player_id and e["type_name"] == "BlockedPass")


def aggregate_match(
    events: list[dict],
    match_data: dict,
    match_id: int,
    competition_id: int,
    season_label: str,
) -> list[dict]:
    """Return list of player_match_stats rows for all players with >0 minutes."""
    max_minute: int = match_data.get("maxMinute") or 90

    # xG/xA come from the fitted WhoScored model — computed once for the match.
    npxg_by_player, xa_by_player, xa_open_by_player, xa_sp_by_player = compute_xg_xa(events)

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

        npxg = npxg_by_player.get(player_id, 0.0)
        xa = xa_by_player.get(player_id, 0.0)
        npxg_plus_xa = npxg + xa
        xa_open = xa_open_by_player.get(player_id, 0.0)
        xa_sp = xa_sp_by_player.get(player_id, 0.0)

        row: dict = {
            "match_id": match_id,
            "player_id": player_id,
            "team_id": p["team_id"],
            "position_played": position,
            "position_bucket": bucket,
            "minutes": minutes,
            "goals": sum(
                1 for e in events if e["player_id"] == player_id and e["type_name"] == "Goal"
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
            "aerials_lost": (
                count_aerials_total(events, player_id) - count_aerials_won(events, player_id)
            ),
            "fouls_drawn": count_fouls_drawn(events, player_id),
            "ball_recoveries": count_ball_recoveries(events, player_id),
            "sca": count_sca(events, player_id),
            "gca": count_gca(events, player_id),
            # --- v2 metrics (SPEC §8.4) ---
            "key_passes": count_key_passes(events, player_id),
            "through_balls_attempted": count_through_balls_attempted(events, player_id),
            "through_balls_completed": count_through_balls_completed(events, player_id),
            "crosses_attempted": count_crosses_attempted(events, player_id),
            "crosses_completed": count_crosses_completed(events, player_id),
            "passes_into_final_third": count_passes_into_final_third(events, player_id),
            "passes_into_box": count_passes_into_box(events, player_id),
            "long_balls_attempted": count_long_balls_attempted(events, player_id),
            "long_balls_completed": count_long_balls_completed(events, player_id),
            "big_chances_created": count_big_chances_created(events, player_id),
            "carries_into_final_third": count_carries_into_final_third(events, player_id),
            "carries_into_box": count_carries_into_box(events, player_id),
            "carry_distance": carry_distance_total(events, player_id),
            "progressive_carry_distance": carry_progressive_distance(events, player_id),
            "miscontrols": count_miscontrols(events, player_id),
            "dispossessed": count_dispossessed(events, player_id),
            "shot_distance_sum": shot_distance_sum(events, player_id),
            "big_chances_faced": count_big_chances_faced(events, player_id),
            "big_chances_scored": count_big_chances_scored(events, player_id),
            "tackles_won": count_tackles_won(events, player_id),
            "tackles_def_third": count_tackles_def_third(events, player_id),
            "tackles_mid_third": count_tackles_mid_third(events, player_id),
            "tackles_att_third": count_tackles_att_third(events, player_id),
            "dribbled_past": count_dribbled_past(events, player_id),
            "errors_leading_to_shot": count_errors_leading_to_shot(events, player_id),
            "xa_open_play": round(xa_open, 4),
            "xa_set_piece": round(xa_sp, 4),
        }

        rows.append(row)

    return rows
