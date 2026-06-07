-- v2 percentile engine (SPEC §8.4 + §9):
--   1. Seed percentile_config minutes thresholds (was empty -> the view returned
--      nothing). 30% of total possible minutes: 38-game leagues (PL/La Liga/
--      Serie A = comp 2/4/5) -> 1026; 34-game leagues -> 918.
--   2. Replace player_season_percentiles to add a percentile column per v2 stat.
--
-- NOTE: a few v2 metrics are "lower is better" (miscontrols_p90, dispossessed_p90,
-- dribbled_past_p90, errors_leading_to_shot_p90, avg_shot_distance). Percentiles
-- here are straight ascending (higher value -> higher percentile); the UI inverts
-- these at display so a high bar always reads as "good".

INSERT INTO percentile_config (season_id, minutes_threshold)
SELECT s.id, CASE WHEN s.competition_id IN (2, 4, 5) THEN 1026 ELSE 918 END
FROM seasons s
ON CONFLICT (season_id) DO UPDATE SET minutes_threshold = EXCLUDED.minutes_threshold;

CREATE OR REPLACE VIEW player_season_percentiles AS
SELECT
  pss.player_id,
  pss.season_id,
  pss.position_bucket,
  pss.minutes,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.npg_p90) * 100 AS npg_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.npxg_p90) * 100 AS npxg_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.shots_p90) * 100 AS shots_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.assists_p90) * 100 AS assists_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.xa_p90) * 100 AS xa_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.npxg_plus_xa_p90) * 100 AS npxg_plus_xa_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.sca_p90) * 100 AS sca_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.gca_p90) * 100 AS gca_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.passes_attempted_p90) * 100 AS passes_attempted_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.pass_completion_pct) * 100 AS pass_completion_pct_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.progressive_passes_p90) * 100 AS progressive_passes_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.progressive_passes_received_p90) * 100 AS progressive_passes_received_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.successful_take_ons_p90) * 100 AS successful_take_ons_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.take_on_success_pct) * 100 AS take_on_success_pct_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.progressive_carries_p90) * 100 AS progressive_carries_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.touches_in_att_pen_area_p90) * 100 AS touches_in_att_pen_area_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.tackles_p90) * 100 AS tackles_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.interceptions_p90) * 100 AS interceptions_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.blocks_p90) * 100 AS blocks_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.clearances_p90) * 100 AS clearances_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.aerials_won_pct) * 100 AS aerials_won_pct_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.fouls_drawn_p90) * 100 AS fouls_drawn_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.ball_recoveries_p90) * 100 AS ball_recoveries_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.shots_on_target_p90) * 100 AS shots_on_target_p90_pct,
  -- v2 metrics (SPEC §8.4)
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.key_passes_p90) * 100 AS key_passes_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.through_balls_p90) * 100 AS through_balls_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.through_ball_completion_pct) * 100 AS through_ball_completion_pct_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.crosses_p90) * 100 AS crosses_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.cross_completion_pct) * 100 AS cross_completion_pct_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.passes_into_final_third_p90) * 100 AS passes_into_final_third_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.passes_into_box_p90) * 100 AS passes_into_box_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.long_balls_p90) * 100 AS long_balls_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.long_ball_completion_pct) * 100 AS long_ball_completion_pct_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.big_chances_created_p90) * 100 AS big_chances_created_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.carries_into_final_third_p90) * 100 AS carries_into_final_third_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.carries_into_box_p90) * 100 AS carries_into_box_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.carry_distance_p90) * 100 AS carry_distance_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.progressive_carry_distance_p90) * 100 AS progressive_carry_distance_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.miscontrols_p90) * 100 AS miscontrols_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.dispossessed_p90) * 100 AS dispossessed_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.shots_on_target_pct) * 100 AS shots_on_target_pct_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.npxg_per_shot) * 100 AS npxg_per_shot_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.avg_shot_distance) * 100 AS avg_shot_distance_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.np_g_minus_xg) * 100 AS np_g_minus_xg_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.big_chances_faced_p90) * 100 AS big_chances_faced_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.big_chance_conversion_pct) * 100 AS big_chance_conversion_pct_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.tackle_win_pct) * 100 AS tackle_win_pct_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.tackles_def_third_p90) * 100 AS tackles_def_third_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.tackles_mid_third_p90) * 100 AS tackles_mid_third_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.tackles_att_third_p90) * 100 AS tackles_att_third_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.dribbled_past_p90) * 100 AS dribbled_past_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.errors_leading_to_shot_p90) * 100 AS errors_leading_to_shot_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.xa_open_play_p90) * 100 AS xa_open_play_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.xa_set_piece_p90) * 100 AS xa_set_piece_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.xt_p90) * 100 AS xt_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.xt_pass_p90) * 100 AS xt_pass_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.xt_carry_p90) * 100 AS xt_carry_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.xg_chain_p90) * 100 AS xg_chain_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.xg_buildup_p90) * 100 AS xg_buildup_p90_pct
FROM player_season_stats pss
WHERE pss.minutes >= (
  SELECT pc.minutes_threshold
  FROM percentile_config pc
  WHERE pc.season_id = pss.season_id
);
