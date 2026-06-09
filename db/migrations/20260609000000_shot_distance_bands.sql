-- Distance-band shot/goal counts (non-penalty), for long-range analysis at
-- player, team, and league level. Additive; back-populated by reprocess.
-- "outside box" = shot location outside the penalty area; "long range" = >=25m
-- from goal centre.
ALTER TABLE player_match_stats
  ADD COLUMN shots_outside_box INT,
  ADD COLUMN goals_outside_box INT,
  ADD COLUMN shots_long_range INT,
  ADD COLUMN goals_long_range INT;
