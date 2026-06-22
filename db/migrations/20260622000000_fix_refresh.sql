-- The refresh function used REFRESH ... CONCURRENTLY for all three views, which
-- exceeded the role's statement_timeout (refresh silently failed -> stale
-- dashboard). Recreate it non-concurrently (faster; a brief refresh-time lock is
-- fine for a daily refresh) with a function-local long statement_timeout.
CREATE OR REPLACE FUNCTION refresh_dashboard_views() RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET statement_timeout = '600s'
AS $$
BEGIN
  REFRESH MATERIALIZED VIEW player_season_percentiles;
  REFRESH MATERIALIZED VIEW team_season_stats;
  REFRESH MATERIALIZED VIEW league_season_stats;
END;
$$;
