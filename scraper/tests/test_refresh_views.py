"""Unit tests for the dashboard view refresh (fake client, no DB).

The bug being locked down: the old refresh made one RPC that rebuilt all three
materialized views under a single statement_timeout, and swallowed the timeout
with a "view refresh skipped" log line. Six consecutive nightly runs went green
while the dashboard served stale percentiles.
"""

import pytest

from src.ingest.season_rollup import _VIEW_REFRESH_RPCS, refresh_dashboard_views


class FakeClient:
    """Records RPC calls. `fail` maps rpc name -> number of times it should raise."""

    def __init__(self, fail=None):
        self.fail = dict(fail or {})
        self.calls: list[str] = []

    def rpc(self, name, _args=None):
        self.calls.append(name)
        if self.fail.get(name, 0) > 0:
            self.fail[name] -= 1
            raise RuntimeError("canceling statement due to statement timeout")
        return self

    def execute(self):
        return type("Res", (), {"data": []})()


def test_refreshes_each_view_as_its_own_call():
    client = FakeClient()
    refresh_dashboard_views(client=client, log=lambda _m: None)
    assert client.calls == list(_VIEW_REFRESH_RPCS)


def test_percentiles_refresh_before_the_heavier_aggregates():
    # Cheapest first: if the run dies partway, the percentile view — the one the
    # scouting reports read — is the one most likely to have made it.
    assert _VIEW_REFRESH_RPCS[0] == "refresh_player_season_percentiles"


def test_a_timed_out_view_is_retried_once_and_succeeds():
    client = FakeClient(fail={"refresh_team_season_stats": 1})
    refresh_dashboard_views(client=client, log=lambda _m: None)
    assert client.calls == [
        "refresh_player_season_percentiles",
        "refresh_team_season_stats",  # timed out
        "refresh_team_season_stats",  # retry, pages now warm
        "refresh_league_season_stats",
    ]


def test_a_view_that_never_refreshes_raises_instead_of_logging_and_moving_on():
    client = FakeClient(fail={"refresh_league_season_stats": 99})
    with pytest.raises(RuntimeError) as e:
        refresh_dashboard_views(client=client, log=lambda _m: None)
    assert "refresh_league_season_stats" in str(e.value)
    assert "stale" in str(e.value)


def test_one_failing_view_does_not_stop_the_others():
    client = FakeClient(fail={"refresh_player_season_percentiles": 99})
    with pytest.raises(RuntimeError):
        refresh_dashboard_views(client=client, log=lambda _m: None)
    assert "refresh_league_season_stats" in client.calls


def test_every_failure_is_reported_not_just_the_first():
    client = FakeClient(
        fail={"refresh_player_season_percentiles": 99, "refresh_league_season_stats": 99}
    )
    with pytest.raises(RuntimeError) as e:
        refresh_dashboard_views(client=client, log=lambda _m: None)
    assert "refresh_player_season_percentiles" in str(e.value)
    assert "refresh_league_season_stats" in str(e.value)
