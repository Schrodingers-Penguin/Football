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
    # No probe for 20260622000000_fix_refresh: 20260802010000 supersedes it, and
    # the thing it probed for (a 600s statement_timeout set inside the function)
    # turned out never to have worked. Probing 20260802010000 covers both.
    Expectation(
        "20260802010000_split_refresh",
        "per-view refresh RPCs",
        # NOTE: this probe has a side effect — it really does refresh the
        # percentiles view. PostgREST can't read pg_proc, so calling the
        # function is the only way to prove it exists. The percentiles view is
        # the cheapest of the three (~12k rows of window functions, vs 200k+ row
        # aggregates for the other two) and the refresh is idempotent, so the
        # cost is one duplicated cheap refresh per run.
        lambda c: c.rpc("refresh_player_season_percentiles").execute(),
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
    Expectation(
        "20260802020000_percentile_config_for_new_seasons",
        "default_minutes_threshold() + percentile_config seeding trigger",
        # The trigger itself isn't visible through PostgREST; its helper function
        # is, and they ship in the same migration. Read-only and instant.
        lambda c: c.rpc("default_minutes_threshold", {"p_competition_id": 2}).execute(),
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
