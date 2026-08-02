"""Verify the live database actually has what db/migrations/ describes.

Migrations here are applied by hand in the Supabase SQL editor, and nothing
checked that it happened. When 20260622010000 (search_players) was skipped, the
web app's fallback swallowed it — accent-insensitive search silently degraded to
accent-sensitive and looked shipped for weeks. The refresh-function fix was
missed the same way, leaving every dashboard percentile stale.

This probes for a distinctive object from each migration and fails loudly. It
checks reality rather than a bookkeeping table, so it can't be fooled by a
migration that was recorded but not run (or run but not recorded).

Add an entry here whenever you add a migration.
"""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Expectation:
    """One probe: `migration` is what to apply if `probe` fails."""

    migration: str
    what: str
    probe: Callable[[object], object]


def _cols(table: str, cols: str) -> Callable[[object], object]:
    return lambda c: c.table(table).select(cols).limit(1).execute()


EXPECTATIONS: tuple[Expectation, ...] = (
    Expectation("20260601000000_initial_schema", "competitions table", _cols("competitions", "id")),
    Expectation("20260601000000_initial_schema", "players table", _cols("players", "id,name")),
    Expectation(
        "20260602000000_add_position_minutes",
        "player_season_stats.position_minutes",
        _cols("player_season_stats", "position_minutes"),
    ),
    Expectation(
        "20260607000000_v2_metrics",
        "v2 metric columns",
        _cols("player_season_stats", "xt_p90,key_passes_p90,tackle_win_pct"),
    ),
    Expectation(
        "20260607010000_v2_percentiles",
        "v2 percentile columns",
        _cols("player_season_percentiles", "xt_p90_pct"),
    ),
    Expectation(
        "20260609000000_shot_distance_bands",
        "shot distance bands",
        _cols("player_match_stats", "shots_long_range"),
    ),
    Expectation(
        "20260609010000_team_league_aggregates",
        "team_season_stats",
        _cols("team_season_stats", "team_id"),
    ),
    Expectation(
        "20260612000000_npxg_split",
        "npxg open-play / set-piece split",
        _cols("player_season_stats", "npxg_open_play_p90,npxg_set_piece_p90"),
    ),
    Expectation(
        "20260619000000_materialize_views",
        "league_season_stats materialized view",
        _cols("league_season_stats", "season_id"),
    ),
    Expectation(
        "20260622000000_fix_refresh",
        "refresh_dashboard_views() with a long statement_timeout",
        # NOTE: this probe has a side effect — it actually refreshes the three
        # materialized views (~13s). That's the only way to tell the fixed
        # function from the broken one through PostgREST, which can't read
        # pg_proc: the pre-fix version dies on the role's 8s cap, this one is
        # allowed 600s. The refresh is idempotent and the daily job does it
        # anyway, so the cost is a duplicated refresh once per run.
        lambda c: c.rpc("refresh_dashboard_views").execute(),
    ),
    Expectation(
        "20260622010000_unaccent_search",
        "search_players() RPC",
        lambda c: c.rpc("search_players", {"q": "a", "lim": 1}).execute(),
    ),
    Expectation(
        "20260802000000_player_age",
        "players.age / players.age_as_of",
        _cols("players", "age,age_as_of"),
    ),
)


def check_schema(client=None) -> list[tuple[Expectation, str]]:
    """Run every probe; return (expectation, error) for each one that failed.

    Not free and not read-only: the refresh_dashboard_views probe rebuilds the
    materialized views (~13s). Run it on a schedule or before a job, not per
    request.
    """
    from .db import get_client

    client = client or get_client()
    failures: list[tuple[Expectation, str]] = []
    for exp in EXPECTATIONS:
        try:
            exp.probe(client)
        except Exception as e:  # noqa: BLE001 — any failure means "not usable"
            failures.append((exp, str(e)[:200]))
    return failures


def assert_schema(client=None, log=print) -> None:
    """Raise if the live schema is missing anything, naming what to apply."""
    failures = check_schema(client)
    if not failures:
        log(f"schema OK ({len(EXPECTATIONS)} checks)")
        return
    lines = [f"{len(failures)} of {len(EXPECTATIONS)} schema checks failed:"]
    for exp, err in failures:
        lines.append(f"  - {exp.what}: apply db/migrations/{exp.migration}.sql")
        lines.append(f"      {err}")
    raise RuntimeError("\n".join(lines))
