/**
 * Composite stats: clusters of base metrics scored as the average of their
 * members' (display-corrected) percentiles within the player's position pool.
 * Member keys reference STAT_CATALOG; lower-is-better members are inverted
 * before averaging (handled by displayPercentile at the call site).
 *
 * Pure config — adjust memberships freely.
 */
export interface CompositeDef {
  key: string;
  label: string;
  members: string[];
}

export const COMPOSITES: readonly CompositeDef[] = [
  {
    key: "shooting",
    label: "Shooting",
    members: [
      "npxg_p90",
      "npg_p90",
      "shots_p90",
      "shots_on_target_pct",
      "npxg_per_shot",
      "big_chances_faced_p90",
    ],
  },
  {
    key: "creation",
    label: "Creation",
    members: [
      "xa_p90",
      "key_passes_p90",
      "sca_p90",
      "big_chances_created_p90",
      "passes_into_box_p90",
    ],
  },
  {
    key: "passing",
    label: "Passing",
    members: [
      "pass_completion_pct",
      "progressive_passes_p90",
      "passes_into_final_third_p90",
      "long_ball_completion_pct",
      "xt_pass_p90",
    ],
  },
  {
    key: "dribbling",
    label: "Dribbling & Carrying",
    members: [
      "successful_take_ons_p90",
      "take_on_success_pct",
      "progressive_carries_p90",
      "carries_into_box_p90",
      "xt_carry_p90",
      "progressive_carry_distance_p90",
    ],
  },
  {
    key: "defending",
    label: "Defending & Duels",
    members: [
      "tackles_p90",
      "tackle_win_pct",
      "interceptions_p90",
      "aerials_won_pct",
      "ball_recoveries_p90",
      "dribbled_past_p90",
    ],
  },
  {
    key: "progression",
    label: "Progression",
    members: [
      "xt_p90",
      "xg_buildup_p90",
      "progressive_passes_p90",
      "progressive_carries_p90",
      "progressive_passes_received_p90",
    ],
  },
] as const;

export const COMPOSITE_BY_KEY: ReadonlyMap<string, CompositeDef> = new Map(
  COMPOSITES.map((c) => [c.key, c]),
);
