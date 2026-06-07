"""Unit tests for season rollup grouping + aggregation (no DB)."""

from src.aggregate.season import aggregate_season, build_player_season_rows


def _ms(player_id, *, minutes, bucket="CM", **stats):
    row = {"player_id": player_id, "position_bucket": bucket, "minutes": minutes}
    row.update(stats)
    return row


def test_groups_by_player_and_attaches_keys():
    stats = [
        _ms(10, minutes=90, goals=1),
        _ms(10, minutes=90, goals=0),
        _ms(20, minutes=45, goals=1),
    ]
    rows = build_player_season_rows(stats, season_id=7)
    by_player = {r["player_id"]: r for r in rows}
    assert set(by_player) == {10, 20}
    assert all(r["season_id"] == 7 for r in rows)


def test_per90_sums_across_matches():
    # 2 goals across 180 minutes -> 1.0 per 90
    stats = [_ms(10, minutes=90, goals=1), _ms(10, minutes=90, goals=1)]
    row = build_player_season_rows(stats, season_id=1)[0]
    assert row["minutes"] == 180
    assert row["goals_p90"] == 1.0


def test_pass_completion_pct_is_ratio_of_totals_not_mean_of_pcts():
    # match A: 100/100, match B: 0/100 -> combined 100/200 = 50%
    stats = [
        _ms(10, minutes=90, passes_completed=100, passes_attempted=100),
        _ms(10, minutes=90, passes_completed=0, passes_attempted=100),
    ]
    row = build_player_season_rows(stats, season_id=1)[0]
    assert row["pass_completion_pct"] == 50.0


def test_sub_threshold_role_dropped_single_row():
    # 80 of 90 min as W (89%), 10 as CF (11%) -> only the W pool, full minutes
    stats = [_ms(10, minutes=80, bucket="W"), _ms(10, minutes=10, bucket="CF")]
    rows = build_player_season_rows(stats, season_id=1)
    assert len(rows) == 1
    assert rows[0]["position_bucket"] == "W"
    assert rows[0]["position_minutes"] == 80
    assert rows[0]["minutes"] == 90  # full-season minutes, not the bucket's


def test_hybrid_appears_in_each_eligible_pool_with_same_stats():
    # 60 min W + 40 min CF, both >=25% -> two rows, identical per-90s,
    # position_minutes split per bucket.
    stats = [
        _ms(10, minutes=60, bucket="W", goals=1),
        _ms(10, minutes=40, bucket="CF", goals=1),
    ]
    rows = build_player_season_rows(stats, season_id=1)
    by_bucket = {r["position_bucket"]: r for r in rows}
    assert set(by_bucket) == {"W", "CF"}
    # FBref-style: same full-season stats in both rows
    assert by_bucket["W"]["goals_p90"] == by_bucket["CF"]["goals_p90"]
    assert by_bucket["W"]["minutes"] == by_bucket["CF"]["minutes"] == 100
    # only the per-bucket sample differs
    assert by_bucket["W"]["position_minutes"] == 60
    assert by_bucket["CF"]["position_minutes"] == 40


def test_player_with_no_bucket_is_dropped():
    stats = [_ms(10, minutes=0, bucket=None)]
    assert build_player_season_rows(stats, season_id=1) == []


def test_empty_input():
    assert build_player_season_rows([], season_id=1) == []
    assert aggregate_season([]) == {}


def test_v2_metrics_rolled_up():
    rows = [
        _ms(10, minutes=90, key_passes=2, tackles=4, tackles_won=3, npg=1, npxg=0.4, xt=0.30),
        _ms(10, minutes=90, key_passes=0, tackles=0, tackles_won=0, npg=0, npxg=0.6, xt=0.10),
    ]
    agg = aggregate_season(rows)
    assert agg["key_passes_p90"] == 1.0  # 2 over 180 min
    assert agg["tackle_win_pct"] == 75.0  # 3/4
    assert agg["xt_p90"] == 0.2  # 0.40 over 180 min
    assert agg["np_g_minus_xg"] == round(1 - 1.0, 4)  # npg 1 - npxg 1.0


def test_v2_ratio_none_when_no_attempts():
    agg = aggregate_season([_ms(10, minutes=90)])
    assert agg["tackle_win_pct"] is None  # no tackles
    assert agg["npxg_per_shot"] is None  # no shots
