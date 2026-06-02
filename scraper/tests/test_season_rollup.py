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


def test_dominant_position_is_minutes_weighted():
    stats = [
        _ms(10, minutes=80, bucket="W"),
        _ms(10, minutes=10, bucket="CF"),
    ]
    row = build_player_season_rows(stats, season_id=1)[0]
    assert row["position_bucket"] == "W"


def test_player_with_no_bucket_is_dropped():
    stats = [_ms(10, minutes=0, bucket=None)]
    assert build_player_season_rows(stats, season_id=1) == []


def test_empty_input():
    assert build_player_season_rows([], season_id=1) == []
    assert aggregate_season([]) == {}
