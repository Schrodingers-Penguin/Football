"""Aggregate player match rows into a season row."""


def build_player_season_rows(match_stats: list[dict], *, season_id: int) -> list[dict]:
    """Group player_match_stats rows by player and aggregate each into a
    player_season_stats row (season_id + player_id + aggregated stats).

    Pure: no DB. One row per player (the dominant-position model in
    `aggregate_season`); players with no position bucket are dropped.
    """
    by_player: dict[int, list[dict]] = {}
    for r in match_stats:
        by_player.setdefault(r["player_id"], []).append(r)

    rows: list[dict] = []
    for player_id, player_rows in by_player.items():
        agg = aggregate_season(player_rows)
        if not agg or agg.get("position_bucket") is None:
            continue
        # FBref-style: one row per eligible bucket, same full-season stats,
        # only position_bucket + position_minutes differ.
        minutes_by_bucket = _bucket_minutes(player_rows)
        for bucket in eligible_position_buckets(player_rows):
            rows.append(
                {
                    "season_id": season_id,
                    "player_id": player_id,
                    **agg,
                    "position_bucket": bucket,
                    "position_minutes": int(minutes_by_bucket.get(bucket, 0)),
                }
            )
    return rows


def aggregate_season(match_rows: list[dict]) -> dict:
    """Aggregate player_match_stats rows into a player_season_stats row.

    Sums raw counts, computes per-90 values and percentage stats.
    """
    if not match_rows:
        return {}

    def _sum(key: str) -> int | float:
        return sum(r.get(key) or 0 for r in match_rows)

    total_minutes = _sum("minutes")

    def _p90(key: str) -> float | None:
        if total_minutes == 0:
            return None
        return round(_sum(key) / total_minutes * 90, 4)

    def _pct(num_key: str, den_key: str) -> float | None:
        den = _sum(den_key)
        if den == 0:
            return None
        return round(_sum(num_key) / den * 100, 2)

    def _ratio(num_key: str, den_key: str, ndigits: int = 4) -> float | None:
        den = _sum(den_key)
        if den == 0:
            return None
        return round(_sum(num_key) / den, ndigits)

    position_bucket = _dominant_position(match_rows)

    return {
        "position_bucket": position_bucket,
        "minutes": int(total_minutes),
        "goals_p90": _p90("goals"),
        "assists_p90": _p90("assists"),
        "npg_p90": _p90("npg"),
        "npxg_p90": _p90("npxg"),
        "xa_p90": _p90("xa"),
        "npxg_plus_xa_p90": _p90("npxg_plus_xa"),
        "shots_p90": _p90("shots"),
        "shots_on_target_p90": _p90("shots_on_target"),
        "passes_attempted_p90": _p90("passes_attempted"),
        "pass_completion_pct": _pct("passes_completed", "passes_attempted"),
        "progressive_passes_p90": _p90("progressive_passes"),
        "progressive_passes_received_p90": _p90("progressive_passes_received"),
        "successful_take_ons_p90": _p90("successful_take_ons"),
        "take_on_success_pct": _pct("successful_take_ons", "take_ons_attempted"),
        "progressive_carries_p90": _p90("progressive_carries"),
        "touches_in_att_pen_area_p90": _p90("touches_in_att_pen_area"),
        "tackles_p90": _p90("tackles"),
        "interceptions_p90": _p90("interceptions"),
        "blocks_p90": _p90("blocks"),
        "clearances_p90": _p90("clearances"),
        "aerials_won_pct": _aerials_won_pct(match_rows),
        "fouls_drawn_p90": _p90("fouls_drawn"),
        "ball_recoveries_p90": _p90("ball_recoveries"),
        "sca_p90": _p90("sca"),
        "gca_p90": _p90("gca"),
        # --- v2 metrics (SPEC §8.4) ---
        "key_passes_p90": _p90("key_passes"),
        "through_balls_p90": _p90("through_balls_attempted"),
        "through_ball_completion_pct": _pct("through_balls_completed", "through_balls_attempted"),
        "crosses_p90": _p90("crosses_attempted"),
        "cross_completion_pct": _pct("crosses_completed", "crosses_attempted"),
        "passes_into_final_third_p90": _p90("passes_into_final_third"),
        "passes_into_box_p90": _p90("passes_into_box"),
        "long_balls_p90": _p90("long_balls_attempted"),
        "long_ball_completion_pct": _pct("long_balls_completed", "long_balls_attempted"),
        "big_chances_created_p90": _p90("big_chances_created"),
        "carries_into_final_third_p90": _p90("carries_into_final_third"),
        "carries_into_box_p90": _p90("carries_into_box"),
        "carry_distance_p90": _p90("carry_distance"),
        "progressive_carry_distance_p90": _p90("progressive_carry_distance"),
        "miscontrols_p90": _p90("miscontrols"),
        "dispossessed_p90": _p90("dispossessed"),
        "shots_on_target_pct": _pct("shots_on_target", "shots"),
        "npxg_per_shot": _ratio("npxg", "shots"),
        "avg_shot_distance": _ratio("shot_distance_sum", "shots", 2),
        "np_g_minus_xg": round(_sum("npg") - _sum("npxg"), 4),
        "big_chances_faced_p90": _p90("big_chances_faced"),
        "big_chance_conversion_pct": _pct("big_chances_scored", "big_chances_faced"),
        "tackle_win_pct": _pct("tackles_won", "tackles"),
        "tackles_def_third_p90": _p90("tackles_def_third"),
        "tackles_mid_third_p90": _p90("tackles_mid_third"),
        "tackles_att_third_p90": _p90("tackles_att_third"),
        "dribbled_past_p90": _p90("dribbled_past"),
        "errors_leading_to_shot_p90": _p90("errors_leading_to_shot"),
        "xa_open_play_p90": _p90("xa_open_play"),
        "xa_set_piece_p90": _p90("xa_set_piece"),
        "xt_p90": _p90("xt"),
        "xt_pass_p90": _p90("xt_pass"),
        "xt_carry_p90": _p90("xt_carry"),
        "xg_chain_p90": _p90("xg_chain"),
        "xg_buildup_p90": _p90("xg_buildup"),
    }


def _aerials_won_pct(match_rows: list[dict]) -> float | None:
    total_won = sum((r.get("aerials_won") or 0) for r in match_rows)
    total_lost = sum((r.get("aerials_lost") or 0) for r in match_rows)
    total = total_won + total_lost
    if total == 0:
        return None
    return round(total_won / total * 100, 2)


_ELIGIBLE_MINUTES_SHARE = 0.25  # SPEC §7: a role counts at >=25% of season minutes


def _bucket_minutes(match_rows: list[dict]) -> dict[str, int]:
    """Minutes played per position bucket (excludes rows with no bucket)."""
    out: dict[str, int] = {}
    for r in match_rows:
        bucket = r.get("position_bucket")
        if bucket is None:
            continue
        out[bucket] = out.get(bucket, 0) + (r.get("minutes") or 0)
    return out


def _dominant_position(match_rows: list[dict]) -> str | None:
    """Minutes-weighted mode of position_bucket across matches."""
    bucket_minutes = _bucket_minutes(match_rows)
    if not bucket_minutes:
        return None
    return max(bucket_minutes, key=lambda b: bucket_minutes[b])


def eligible_position_buckets(match_rows: list[dict]) -> list[str]:
    """Buckets the player should be pooled in: those with >=25% of their season
    minutes. Always includes at least the dominant bucket so every player lands
    in exactly one pool when they don't split roles. Sorted for stable output.
    """
    bucket_minutes = _bucket_minutes(match_rows)
    if not bucket_minutes:
        return []
    total = sum(bucket_minutes.values())
    if total == 0:  # bucketed but zero minutes — fall back to the dominant bucket
        return [_dominant_position(match_rows)]
    eligible = [b for b, m in bucket_minutes.items() if m / total >= _ELIGIBLE_MINUTES_SHARE]
    return sorted(eligible) if eligible else [_dominant_position(match_rows)]
