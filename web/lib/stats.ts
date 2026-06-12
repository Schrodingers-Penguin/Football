/**
 * Canonical stat catalogue — the single source of truth for which metrics exist,
 * how they're labelled, grouped, and formatted (SPEC §14: never hardcode the stat
 * list in components). Both the API and the UI derive from this.
 *
 * `key` is the column name in `player_season_stats`; its percentile column in the
 * `player_season_percentiles` view is `${key}_pct`.
 *
 * `lowerIsBetter` flags metrics where a low raw value is good (miscontrols, being
 * dribbled past, …). Their stored percentile is straight ascending, so the UI
 * inverts it (display percentile = 100 − stored) and reads "higher bar = better".
 */
export type StatCategory = "attacking" | "passing" | "possession" | "defending";
export type StatFormat = "per90" | "percent" | "value";

export interface StatDef {
  key: string;
  label: string;
  category: StatCategory;
  format: StatFormat;
  lowerIsBetter?: boolean;
}

export const STAT_CATALOG: readonly StatDef[] = [
  // --- attacking / shooting ---
  { key: "npg_p90", label: "Non-Penalty Goals", category: "attacking", format: "per90" },
  { key: "npxg_p90", label: "npxG", category: "attacking", format: "per90" },
  { key: "npxg_open_play_p90", label: "npxG (Open Play)", category: "attacking", format: "per90" },
  { key: "npxg_set_piece_p90", label: "npxG (Set Piece)", category: "attacking", format: "per90" },
  { key: "np_g_minus_xg", label: "Goals − npxG", category: "attacking", format: "value" },
  { key: "shots_p90", label: "Shots", category: "attacking", format: "per90" },
  { key: "shots_on_target_pct", label: "Shots on Target %", category: "attacking", format: "percent" },
  { key: "npxg_per_shot", label: "npxG / Shot", category: "attacking", format: "value" },
  { key: "avg_shot_distance", label: "Avg Shot Distance (m)", category: "attacking", format: "value", lowerIsBetter: true },
  { key: "big_chances_faced_p90", label: "Big Chances", category: "attacking", format: "per90" },
  { key: "big_chance_conversion_pct", label: "Big Chance Conv. %", category: "attacking", format: "percent" },
  { key: "touches_in_att_pen_area_p90", label: "Touches in Box", category: "attacking", format: "per90" },

  // --- creation / passing ---
  { key: "assists_p90", label: "Assists", category: "passing", format: "per90" },
  { key: "xa_p90", label: "xA", category: "passing", format: "per90" },
  { key: "npxg_plus_xa_p90", label: "npxG + xA", category: "passing", format: "per90" },
  { key: "xa_open_play_p90", label: "xA (Open Play)", category: "passing", format: "per90" },
  { key: "xa_set_piece_p90", label: "xA (Set Piece)", category: "passing", format: "per90" },
  { key: "sca_p90", label: "Shot-Creating Actions", category: "passing", format: "per90" },
  { key: "gca_p90", label: "Goal-Creating Actions", category: "passing", format: "per90" },
  { key: "key_passes_p90", label: "Key Passes", category: "passing", format: "per90" },
  { key: "big_chances_created_p90", label: "Big Chances Created", category: "passing", format: "per90" },
  { key: "passes_attempted_p90", label: "Passes Attempted", category: "passing", format: "per90" },
  { key: "pass_completion_pct", label: "Pass Completion %", category: "passing", format: "percent" },
  { key: "progressive_passes_p90", label: "Progressive Passes", category: "passing", format: "per90" },
  { key: "passes_into_final_third_p90", label: "Passes into Final Third", category: "passing", format: "per90" },
  { key: "passes_into_box_p90", label: "Passes into Box", category: "passing", format: "per90" },
  { key: "through_balls_p90", label: "Through Balls", category: "passing", format: "per90" },
  { key: "crosses_p90", label: "Crosses", category: "passing", format: "per90" },
  { key: "long_balls_p90", label: "Long Balls", category: "passing", format: "per90" },
  { key: "long_ball_completion_pct", label: "Long Ball %", category: "passing", format: "percent" },

  // --- possession / progression ---
  { key: "xt_p90", label: "Expected Threat (xT)", category: "possession", format: "per90" },
  { key: "xt_pass_p90", label: "xT from Passes", category: "possession", format: "per90" },
  { key: "xt_carry_p90", label: "xT from Carries", category: "possession", format: "per90" },
  { key: "xg_chain_p90", label: "xGChain", category: "possession", format: "per90" },
  { key: "xg_buildup_p90", label: "xGBuildup", category: "possession", format: "per90" },
  { key: "progressive_passes_received_p90", label: "Prog. Passes Received", category: "possession", format: "per90" },
  { key: "successful_take_ons_p90", label: "Successful Take-Ons", category: "possession", format: "per90" },
  { key: "take_on_success_pct", label: "Take-On Success %", category: "possession", format: "percent" },
  { key: "progressive_carries_p90", label: "Progressive Carries", category: "possession", format: "per90" },
  { key: "progressive_carry_distance_p90", label: "Prog. Carry Distance (m)", category: "possession", format: "per90" },
  { key: "carries_into_final_third_p90", label: "Carries into Final Third", category: "possession", format: "per90" },
  { key: "carries_into_box_p90", label: "Carries into Box", category: "possession", format: "per90" },
  { key: "miscontrols_p90", label: "Miscontrols", category: "possession", format: "per90", lowerIsBetter: true },
  { key: "dispossessed_p90", label: "Dispossessed", category: "possession", format: "per90", lowerIsBetter: true },

  // --- defending ---
  { key: "tackles_p90", label: "Tackles", category: "defending", format: "per90" },
  { key: "tackle_win_pct", label: "Tackle Win %", category: "defending", format: "percent" },
  { key: "tackles_def_third_p90", label: "Tackles (Def 3rd)", category: "defending", format: "per90" },
  { key: "tackles_mid_third_p90", label: "Tackles (Mid 3rd)", category: "defending", format: "per90" },
  { key: "tackles_att_third_p90", label: "Tackles (Att 3rd)", category: "defending", format: "per90" },
  { key: "interceptions_p90", label: "Interceptions", category: "defending", format: "per90" },
  { key: "blocks_p90", label: "Blocks", category: "defending", format: "per90" },
  { key: "clearances_p90", label: "Clearances", category: "defending", format: "per90" },
  { key: "dribbled_past_p90", label: "Dribbled Past", category: "defending", format: "per90", lowerIsBetter: true },
  { key: "errors_leading_to_shot_p90", label: "Errors → Shot", category: "defending", format: "per90", lowerIsBetter: true },
  { key: "aerials_won_pct", label: "Aerials Won %", category: "defending", format: "percent" },
  { key: "ball_recoveries_p90", label: "Ball Recoveries", category: "defending", format: "per90" },
  { key: "fouls_drawn_p90", label: "Fouls Drawn", category: "defending", format: "per90" },
] as const;

export const STAT_BY_KEY: ReadonlyMap<string, StatDef> = new Map(
  STAT_CATALOG.map((s) => [s.key, s]),
);

export const CATEGORY_ORDER: readonly StatCategory[] = [
  "attacking",
  "passing",
  "possession",
  "defending",
];

/**
 * Team/league aggregate catalogue. `key` is a column in team_season_stats /
 * league_season_stats (a SUM of the underlying per-match stat). `ratio` marks a
 * value that's already a percentage (not summable / per-match). Everything else
 * is a total with a meaningful per-match rate (total / matches_played).
 */
export interface TeamStatDef {
  key: string;
  label: string;
  category: StatCategory;
  ratio?: boolean;
}

export const TEAM_STAT_CATALOG: readonly TeamStatDef[] = [
  { key: "goals", label: "Goals", category: "attacking" },
  { key: "npxg", label: "npxG", category: "attacking" },
  { key: "npxg_open_play", label: "npxG (Open Play)", category: "attacking" },
  { key: "npxg_set_piece", label: "npxG (Set Piece)", category: "attacking" },
  { key: "shots", label: "Shots", category: "attacking" },
  { key: "shots_on_target", label: "Shots on Target", category: "attacking" },
  { key: "goals_long_range", label: "Long-Range Goals", category: "attacking" },
  { key: "shots_long_range", label: "Long-Range Shots", category: "attacking" },
  { key: "goals_outside_box", label: "Goals Outside Box", category: "attacking" },
  { key: "shots_outside_box", label: "Shots Outside Box", category: "attacking" },
  { key: "big_chances_faced", label: "Big Chances", category: "attacking" },
  { key: "big_chances_created", label: "Big Chances Created", category: "passing" },
  { key: "key_passes", label: "Key Passes", category: "passing" },
  { key: "progressive_passes", label: "Progressive Passes", category: "passing" },
  { key: "passes_into_box", label: "Passes into Box", category: "passing" },
  { key: "crosses_attempted", label: "Crosses", category: "passing" },
  { key: "through_balls_attempted", label: "Through Balls", category: "passing" },
  { key: "pass_completion_pct", label: "Pass Completion %", category: "passing", ratio: true },
  { key: "xt", label: "Expected Threat (xT)", category: "possession" },
  { key: "xg_chain", label: "xGChain", category: "possession" },
  { key: "successful_take_ons", label: "Successful Take-Ons", category: "possession" },
  { key: "progressive_carries", label: "Progressive Carries", category: "possession" },
  { key: "tackles", label: "Tackles", category: "defending" },
  { key: "interceptions", label: "Interceptions", category: "defending" },
  { key: "clearances", label: "Clearances", category: "defending" },
  { key: "aerials_won", label: "Aerials Won", category: "defending" },
] as const;

export const TEAM_STAT_BY_KEY: ReadonlyMap<string, TeamStatDef> = new Map(
  TEAM_STAT_CATALOG.map((s) => [s.key, s]),
);
