-- Hybrid players appear in one player_season_stats row per eligible position
-- bucket (>=25% of season minutes), each carrying the SAME full-season per-90
-- stats (FBref-style: switch the comparison pool, not the numbers). All those
-- rows share the player's total `minutes`, so on its own that column can no
-- longer tell us which role is primary or how big each role's sample is.
--
-- position_minutes records the minutes the player logged IN THIS bucket. The UI
-- defaults a hybrid to their largest-position row and can flag small samples.
ALTER TABLE player_season_stats
  ADD COLUMN position_minutes INT;
