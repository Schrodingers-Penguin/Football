"""Unit tests for the schema drift check (fake client, no DB)."""

import pytest

from src.schema_check import EXPECTATIONS, Expectation, assert_schema, check_schema


class FakeClient:
    """Fails any probe touching a name in `missing`."""

    def __init__(self, missing=()):
        self.missing = set(missing)

    def table(self, name):
        if name in self.missing:
            raise RuntimeError(f'relation "{name}" does not exist')
        return self

    def rpc(self, name, _args=None):
        if name in self.missing:
            raise RuntimeError(f"Could not find the function public.{name}")
        return self

    def select(self, cols):
        for c in cols.split(","):
            if c in self.missing:
                raise RuntimeError(f'column "{c}" does not exist')
        return self

    def limit(self, _n):
        return self

    def execute(self):
        return type("Res", (), {"data": []})()


def test_healthy_schema_has_no_failures():
    assert check_schema(FakeClient()) == []


def test_missing_table_is_reported():
    failures = check_schema(FakeClient({"team_season_stats"}))
    assert len(failures) == 1
    assert failures[0][0].migration == "20260609010000_team_league_aggregates"


def test_missing_rpc_is_reported():
    failures = check_schema(FakeClient({"search_players"}))
    assert [f[0].migration for f in failures] == ["20260622010000_unaccent_search"]


def test_missing_column_is_reported():
    failures = check_schema(FakeClient({"age"}))
    assert [f[0].migration for f in failures] == ["20260802000000_player_age"]


def test_assert_schema_raises_naming_the_migration_to_apply():
    with pytest.raises(RuntimeError) as e:
        assert_schema(FakeClient({"search_players"}))
    assert "db/migrations/20260622010000_unaccent_search.sql" in str(e.value)


def test_assert_schema_passes_on_a_healthy_schema():
    assert_schema(FakeClient(), log=lambda _m: None)


def test_every_expectation_names_a_real_migration_file():
    from pathlib import Path

    migrations = Path(__file__).parents[2] / "db" / "migrations"
    for exp in EXPECTATIONS:
        assert (migrations / f"{exp.migration}.sql").exists(), exp.migration


def test_expectations_are_not_empty():
    assert len(EXPECTATIONS) >= 10
    assert all(isinstance(e, Expectation) for e in EXPECTATIONS)
