-- Substitutes were dropped from player_match_stats entirely (position_bucket
-- NOT NULL), so a sub's goals/shots/etc. were missing from BOTH the player's
-- own season totals and team/league totals. Allow NULL position_bucket so
-- substitute appearances are stored. The season rollup assigns a player's
-- position pool from their bucketed (started) minutes and drops players who
-- only ever appeared as a sub with no position, so scouting pools are unchanged.
ALTER TABLE player_match_stats
  ALTER COLUMN position_bucket DROP NOT NULL;
