-- Why: every daily cron run since at least 2026-07-26 ended with
--   view refresh skipped (57014: canceling statement due to statement timeout)
-- leaving all three dashboard materialized views stale. Ad-hoc daytime calls
-- succeed (13.9s from a laptop, 18.7s from a GitHub runner), so the refresh sits
-- right at the role's statement_timeout and the 02:00 UTC run — the day's first
-- query, against a cold free-tier instance — goes over it.
--
-- 20260622000000_fix_refresh tried to solve this with `SET statement_timeout =
-- '600s'` on the function. That does nothing: Postgres arms the statement timer
-- in start_xact_command, before the function body runs, and changing the GUC
-- mid-statement does not re-arm the timer for the statement already in flight.
-- The proof is the failure itself — a function nominally allowed 600s was being
-- killed by statement_timeout. Do not re-add that SET; it reads like a fix and
-- isn't one.
--
-- Fix: one function per view. The ingest calls them as three separate PostgREST
-- statements, so each gets its own full timeout budget instead of sharing one.
-- refresh_dashboard_views() stays as a wrapper for manual/SQL-editor use, but
-- nothing on the timeout-sensitive path should call it.

CREATE OR REPLACE FUNCTION refresh_player_season_percentiles() RETURNS void
LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  REFRESH MATERIALIZED VIEW player_season_percentiles;
END;
$$;

CREATE OR REPLACE FUNCTION refresh_team_season_stats() RETURNS void
LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  REFRESH MATERIALIZED VIEW team_season_stats;
END;
$$;

CREATE OR REPLACE FUNCTION refresh_league_season_stats() RETURNS void
LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  REFRESH MATERIALIZED VIEW league_season_stats;
END;
$$;

-- Convenience wrapper: all three in one call. Subject to a single
-- statement_timeout budget, so it is for interactive use only.
CREATE OR REPLACE FUNCTION refresh_dashboard_views() RETURNS void
LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  PERFORM refresh_player_season_percentiles();
  PERFORM refresh_team_season_stats();
  PERFORM refresh_league_season_stats();
END;
$$;

-- New functions must appear in PostgREST's schema cache before the scraper can
-- call them. Supabase reloads on DDL automatically; this makes it deterministic.
NOTIFY pgrst, 'reload schema';
