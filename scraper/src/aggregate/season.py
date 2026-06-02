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
        rows.append({"season_id": season_id, "player_id": player_id, **agg})
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
    }


def _aerials_won_pct(match_rows: list[dict]) -> float | None:
    total_won = sum((r.get("aerials_won") or 0) for r in match_rows)
    total_lost = sum((r.get("aerials_lost") or 0) for r in match_rows)
    total = total_won + total_lost
    if total == 0:
        return None
    return round(total_won / total * 100, 2)


def _dominant_position(match_rows: list[dict]) -> str | None:
    """Minutes-weighted mode of position_bucket across matches."""
    bucket_minutes: dict[str, int] = {}
    for r in match_rows:
        bucket = r.get("position_bucket")
        if bucket is None:
            continue
        bucket_minutes[bucket] = bucket_minutes.get(bucket, 0) + (r.get("minutes") or 0)

    if not bucket_minutes:
        return None

    total = sum(bucket_minutes.values())
    best_bucket = max(bucket_minutes, key=lambda b: bucket_minutes[b])
    best_minutes = bucket_minutes[best_bucket]

    if best_minutes / total >= 0.25:
        return best_bucket

    return best_bucket
