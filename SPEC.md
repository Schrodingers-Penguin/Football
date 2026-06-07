# Football Scouting Dashboard — Build Specification

A personal-use FBref-style scouting dashboard. Replicates FBref's per-player percentile scouting report using event-level data scraped from WhoScored. Not for publication.

---

## 1. Goal

For any player in scope, show their per-90 stats benchmarked as percentiles against same-position peers in the same league and season. Update daily as matches complete.

## 2. Non-goals

- Live / in-match data
- Pass maps, shot maps, heatmaps (could be added later if Postgres event-store is adopted)
- Goalkeeper scouting reports (deferred to a future phase)
- Public hosting, sharing access with others, monetisation
- Match prediction or betting model integration

## 3. Tech stack

| Layer | Choice |
|---|---|
| Scraper | Python 3.11+, Playwright (with stealth), GitHub Actions cron |
| Database | Supabase (Postgres) — new project, free tier |
| Object storage | Supabase Storage (for raw match JSONs) |
| Backend / API | Next.js 14 API routes + Supabase JS client |
| Frontend | Next.js 14, React, Tailwind, recharts (or d3) |
| Frontend hosting | Vercel (hobby tier) |
| Repo | Single GitHub repo (monorepo: `/scraper`, `/web`) |

## 4. Scope

### Competitions (8)

| Competition | WhoScored ID region |
|---|---|
| Premier League | England |
| La Liga | Spain |
| Bundesliga | Germany |
| Serie A | Italy |
| Ligue 1 | France |
| Eredivisie | Netherlands |
| Primeira Liga | Portugal |
| UEFA Champions League | Europe (full competition incl. league/group phase) |

### Seasons (3)

- 2023–24 (backfill)
- 2024–25 (backfill)
- 2025–26 (current; daily updates)

Estimated total: ~7,500–7,700 matches.

### Players

All players who feature in any in-scope match.

## 5. Architecture

```
WhoScored match page
        │
        ▼
Playwright scraper (Python, GitHub Actions or local)
        │
        ├─→ Raw matchCentreData JSON → Supabase Storage (verbatim, gzipped)
        │
        └─→ In-memory parser
                │
                ▼
        Event tagging functions (progressive pass, SCA, etc.)
                │
                ▼
        player_match_stats (one row per player per match)
                │
                ▼ (aggregate)
        player_season_stats (one row per player per season per competition)
                │
                ▼
        SQL view: percentile vs position pool
                │
                ▼
        Next.js API → React UI
```

**Storage pattern: hybrid.** Raw JSONs in Supabase Storage (cheap object storage). Parsed events are not persisted — processed in memory during ingestion. Only aggregates live in Postgres. This keeps Supabase free tier viable. Adding a new metric later means re-running the parser against the stored JSONs (estimated 15–20 minutes for a full reprocess), not re-scraping.

## 6. Database schema (Postgres)

```sql
-- Competitions
CREATE TABLE competitions (
  id INT PRIMARY KEY,                    -- WhoScored competition id
  name TEXT NOT NULL,
  country TEXT NOT NULL
);

-- Seasons
CREATE TABLE seasons (
  id SERIAL PRIMARY KEY,
  competition_id INT NOT NULL REFERENCES competitions(id),
  season_label TEXT NOT NULL,            -- e.g. '2025-2026'
  UNIQUE (competition_id, season_label)
);

-- Teams
CREATE TABLE teams (
  id INT PRIMARY KEY,                    -- WhoScored team id
  name TEXT NOT NULL,
  short_name TEXT,
  country TEXT
);

-- Players
CREATE TABLE players (
  id INT PRIMARY KEY,                    -- WhoScored player id
  name TEXT NOT NULL,
  birth_date DATE,
  nationality TEXT,
  preferred_foot TEXT,
  height_cm INT
);

-- Matches
CREATE TABLE matches (
  id BIGINT PRIMARY KEY,                 -- WhoScored match id
  competition_id INT NOT NULL REFERENCES competitions(id),
  season_id INT NOT NULL REFERENCES seasons(id),
  kickoff TIMESTAMPTZ NOT NULL,
  home_team_id INT NOT NULL REFERENCES teams(id),
  away_team_id INT NOT NULL REFERENCES teams(id),
  home_score INT,
  away_score INT,
  status TEXT NOT NULL,                  -- 'finished', 'scheduled', 'postponed'
  raw_json_path TEXT,                    -- path in Supabase Storage
  ingested_at TIMESTAMPTZ
);

-- Player match stats (one row per player per match)
CREATE TABLE player_match_stats (
  id BIGSERIAL PRIMARY KEY,
  match_id BIGINT NOT NULL REFERENCES matches(id),
  player_id INT NOT NULL REFERENCES players(id),
  team_id INT NOT NULL REFERENCES teams(id),
  position_played TEXT NOT NULL,         -- WhoScored code: GK, DC, DL, DR, etc.
  position_bucket TEXT NOT NULL,         -- our taxonomy: GK, CB, FB, DM, CM, AM, W, CF
  minutes INT NOT NULL,
  -- all raw stat counts (not per-90) follow; per-90 computed at aggregate level
  goals INT, assists INT, npg INT,
  npxg NUMERIC, xa NUMERIC, npxg_plus_xa NUMERIC,
  shots INT, shots_on_target INT,
  passes_attempted INT, passes_completed INT,
  progressive_passes INT, progressive_passes_received INT,
  successful_take_ons INT, take_ons_attempted INT,
  progressive_carries INT,
  touches_in_att_pen_area INT,
  tackles INT, interceptions INT, blocks INT, clearances INT,
  aerials_won INT, aerials_lost INT,
  fouls_drawn INT, ball_recoveries INT,
  sca INT, gca INT,
  UNIQUE (match_id, player_id)
);

-- Player season stats (aggregated, with per-90 and percentile-ready columns)
CREATE TABLE player_season_stats (
  id BIGSERIAL PRIMARY KEY,
  season_id INT NOT NULL REFERENCES seasons(id),
  player_id INT NOT NULL REFERENCES players(id),
  position_bucket TEXT NOT NULL,
  minutes INT NOT NULL,
  -- per-90 values for every stat
  goals_p90 NUMERIC, assists_p90 NUMERIC, npg_p90 NUMERIC,
  npxg_p90 NUMERIC, xa_p90 NUMERIC, npxg_plus_xa_p90 NUMERIC,
  shots_p90 NUMERIC, shots_on_target_p90 NUMERIC,
  passes_attempted_p90 NUMERIC, pass_completion_pct NUMERIC,
  progressive_passes_p90 NUMERIC, progressive_passes_received_p90 NUMERIC,
  successful_take_ons_p90 NUMERIC, take_on_success_pct NUMERIC,
  progressive_carries_p90 NUMERIC,
  touches_in_att_pen_area_p90 NUMERIC,
  tackles_p90 NUMERIC, interceptions_p90 NUMERIC,
  blocks_p90 NUMERIC, clearances_p90 NUMERIC,
  aerials_won_pct NUMERIC,
  fouls_drawn_p90 NUMERIC, ball_recoveries_p90 NUMERIC,
  sca_p90 NUMERIC, gca_p90 NUMERIC,
  last_updated TIMESTAMPTZ DEFAULT now(),
  UNIQUE (season_id, player_id, position_bucket)
);

CREATE INDEX idx_pss_season_position ON player_season_stats (season_id, position_bucket);
CREATE INDEX idx_pms_match ON player_match_stats (match_id);
CREATE INDEX idx_pms_player ON player_match_stats (player_id);
```

### Object storage layout

```
supabase-storage://raw-matches/
  └─ <competition_id>/
      └─ <season_label>/
          └─ <match_id>.json.gz
```

## 7. Position taxonomy

WhoScored per-match position code → our bucket:

| WhoScored code | Bucket |
|---|---|
| GK | GK |
| DC | CB |
| DL, DR | FB |
| DMC, DML, DMR | DM |
| MC, ML, MR | CM |
| AMC | AM |
| AML, AMR | W |
| FW (FWL, FWR if present) | CF |
| Sub (no position played) | (excluded — minutes still counted toward team total but no position assignment) |

**Player season position assignment**: minutes-weighted mode across all matches played that season. Tie-break: prefer attacking position (further up the table above). Stored on `player_season_stats.position_bucket`. A player who genuinely splits between two roles will appear in two rows (one per bucket) only if minutes in both are ≥ 25% of total — otherwise the dominant position wins outright.

## 8. Stat definitions

All stats are computed from WhoScored event data. Definitions match FBref's published methodology (which mirrors Opta). Where event data lacks granularity, the implementation note flags it.

### 8.1 Coordinate system reminder

WhoScored coordinates: x ∈ [0, 100], y ∈ [0, 100]. **Verify in Phase 1**: confirm whether x is always team-attack-normalised (each team attacks toward x=100) or pitch-absolute. The matchCentreData JSON typically has events already normalised per team; confirm this empirically against a known match before relying on it.

### 8.2 Stat list (20 stats, all outfield players)

| # | Stat | Definition |
|---|---|---|
| 1 | Non-Penalty Goals | Goal events (event_type=Goal) excluding penalties (qualifier=Penalty) |
| 2 | npxG | Sum of expected goals from non-penalty shots. WhoScored exposes xG per shot in event qualifiers |
| 3 | Shots | All shot events (Goal, MissedShots, SavedShot, ShotOnPost) excluding penalties |
| 4 | Assists | Pass events with qualifier=IntentionalGoalAssist, attributed to the passer |
| 5 | xA (Expected Assisted Goals) | Sum of xG of shots resulting from this player's key passes |
| 6 | npxG + xA | Sum of (2) and (5) |
| 7 | Shot-Creating Actions (SCA) | The two offensive actions immediately preceding any shot. Eligible action types: live-ball pass, dead-ball pass, take-on, drawn foul, defensive action winning possession, another shot leading to rebound. Same player credited at most once per shot. |
| 8 | Passes Attempted | Pass events (any outcome) |
| 9 | Pass Completion % | Completed passes / Attempted passes × 100 |
| 10 | Progressive Passes | Completed passes moving the ball ≥10 yards closer to the opponent's goal line measured from the furthest point in the previous 6 passes, OR any completed pass into the penalty area. **Excludes passes originating from the defending 40% of the pitch (start_x < 40).** |
| 11 | Progressive Passes Received | Count of passes received by this player that meet the progressive criteria. Requires reverse-lookup from completed progressive passes (passer's event end_x/end_y matches receiver's next touch). |
| 12 | Successful Take-Ons | Successful 1v1 dribbles past an opponent. WhoScored: TakeOn event with outcome=Successful. |
| 13 | Take-On Success % | Successful / Attempted × 100 |
| 14 | Progressive Carries | A carry that moves the ball ≥10 yards toward the opponent's goal OR into the penalty area. **Excludes carries originating in the defending 40% of the pitch.** WhoScored doesn't directly tag "carry" events — derive from consecutive touch events by the same player between two non-carry actions. |
| 15 | Touches in Attacking Penalty Area | Touch events where x ≥ 83 and 21 ≤ y ≤ 79 (standard penalty-area bounding box in WhoScored's 100×100 grid) |
| 16 | Tackles | Tackle events |
| 17 | Interceptions | Interception events |
| 18 | Blocks | Block events (shot blocks and pass blocks combined, mirroring FBref's column) |
| 19 | Clearances | Clearance events |
| 20 | Aerials Won % | Aerials won / (won + lost) × 100. Both come from Aerial event qualifiers. |
| 21 | Fouls Drawn | Foul events where this player was the recipient (qualifier or paired Foul/FoulCommitted event) |
| 22 | Ball Recoveries | BallRecovery event count |
| 23 | Goal-Creating Actions (GCA) | As SCA but only for shots resulting in a goal |

**Stat count is 23, not 20.** FBref's exact 20 varies slightly by position; we include the union and let the UI show position-relevant subsets.

### 8.3 Stats that look easy but require care

- **Progressive passes**: the "furthest point in last 6 passes" rule is a refinement most implementations skip. Phase 3 should produce both a simplified version (just ≥10 yards forward, excluding defensive 40%) and the strict version with the 6-pass lookback. Default the UI to the strict version once both are validated against a published reference.
- **Progressive passes received**: requires reverse lookup. Build from the progressive passes table by matching `pass.end_x ≈ next_event_for_team.x` and `pass.end_y ≈ next_event_for_team.y` within a small tolerance, attributed to the receiver.
- **Carries**: not a primary event in WhoScored. Derive by stitching consecutive touches by the same player. A carry's start = first touch by player after gaining possession; end = the touch immediately before they pass, shoot, lose possession, or are dispossessed. Distance is the straight-line between start and end.
- **SCA / GCA**: walk back through the event stream from each shot, picking up to two preceding offensive actions by *different* events (same player can be credited for one of the two slots but not both).

### 8.4 Additional metrics (v2)

Additive to the 23 in §8.2. All are derivable from the stored `matchCentreData` — the source qualifier/event for each was verified against a real match's event vocabulary — so they are added by **reprocessing the stored raw JSONs, not re-scraping** (SPEC §5).

Conventions reused from §8.1–§8.2: coordinates `x, y ∈ [0,100]` with each team attacking toward `x=100` (verified Phase 1); **penalty area** = `x ≥ 83 ∧ 21 ≤ y ≤ 79`; **final third** = `x ≥ 66.67`; distances converted to metres via a 105×68 pitch. "Completed" = `outcomeType=Successful`. Penalty-context stats use **non-penalty** events to stay consistent with npxG/npG.

**Normalization:** `player_match_stats` stores raw counts/sums **and** ratio components (so season ratios are summed-then-divided, never an average of per-match percentages). `player_season_stats` stores the per-90s, ratios, and differences below, and the percentile view gains one column per metric.

#### Passing & creation

| Metric | Definition | Source (verified) | Season form |
|---|---|---|---|
| Key passes | Passes carrying `KeyPass` (a pass directly leading to a shot; superset of assists) | `KeyPass` qualifier | per-90 |
| Through balls | Passes carrying `Throughball` | `Throughball` qualifier | per-90 |
| Crosses | Open-play passes carrying `Cross` | `Cross` qualifier | per-90 |
| Passes into final third | Completed passes with `start_x < 66.67 ≤ end_x` (open play) | `PassEndX` | per-90 |
| Passes into penalty area | Completed open-play passes ending in the box from a start outside it | `PassEndX/Y` | per-90 |
| Long-ball completion % | Completed `Longball` passes ÷ attempted `Longball` passes | `Longball` qualifier + outcome | ratio |
| Big chances created | Passes carrying `BigChanceCreated` | `BigChanceCreated` qualifier | per-90 |

#### Carrying & possession (carries derived per §8.3)

| Metric | Definition | Source | Season form |
|---|---|---|---|
| Carries into final third | Carries with `start_x < 66.67 ≤ end_x` | derived carry | per-90 |
| Carries into penalty area | Carries ending in the box from a start outside it | derived carry | per-90 |
| Total carry distance | Σ straight-line carry length (m) | derived carry | per-90 (m/90) |
| Progressive carry distance ("fields gained") | Σ toward-goal distance = Σ max(0, end_x − start_x) in metres | derived carry | per-90 |
| Miscontrols | `BallTouch` events with `Unsuccessful` outcome | `BallTouch` + outcome | per-90 |
| Dispossessed | `Dispossessed` events | `Dispossessed` event | per-90 |

#### Shooting quality (non-penalty unless noted)

| Metric | Definition | Source | Season form |
|---|---|---|---|
| Shots on target % | (Goal + SavedShot) ÷ non-penalty shots — on-frame only (excludes blocked, off-target, woodwork) | shot event types | ratio |
| npxG per shot | npxG ÷ non-penalty shots | xG model | ratio |
| Average shot distance | Mean distance from shot `(x,y)` to goal centre `(100,50)`, metres, non-penalty shots | shot coords | value |
| G − xG (finishing) | Non-penalty goals − npxG | goals + xG model | difference (also per-90) |

#### Defending

| Metric | Definition | Source | Season form |
|---|---|---|---|
| Tackle win % | Successful `Tackle` ÷ all `Tackle` | `Tackle` outcomeType | ratio |
| Tackles by third | `Tackle` counts split by x-zone: def `<33.3`, mid `33.3–66.67`, att `≥66.67` | `Tackle` coords | per-90 (×3) |
| Times dribbled past | `Challenge` events (defender beaten by a take-on) | `Challenge` event | per-90 |
| Errors leading to a shot | `Error` events carrying `LeadingToAttempt` | `Error` + `LeadingToAttempt` | per-90 |

#### Creation split

| Metric | Definition | Source | Season form |
|---|---|---|---|
| xA (open play) / xA (set piece) | Existing xA partitioned by the key pass's situation: set-piece if the pass carries `CornerTaken` / `FreekickTaken` / `IndirectFreekickTaken` / `ThrowIn` / `FromCorner` / `SetPiece`, else open play. Sum = total xA | pass set-piece qualifiers + xG model | per-90 (×2) |

#### 8.4.1 Expected Threat (xT) — fit our own

xT is **modelled**, not tagged. We fit our own grid on our ~7,000-match event set (consistent with the WhoScored-native xG decision; avoids the coordinate-transfer error of a foreign grid).

- **Grid:** 16×12 (Karun Singh possession-value formulation), attack toward `x=100`, **open-play moves only** in the transition model (set pieces excluded so they don't distort zone transitions).
- **Fit:** per cell, from the data — `P(shot)`, `P(goal|shot)` (zone scoring rate), `P(move)`, and the move transition matrix `T[z→z']` from successful passes + carries. Iterate `xT[z] = P(shot)·P(goal|shot) + P(move)·Σ T[z→z']·xT[z']` to convergence.
- **Player credit:** for each successful open-play pass/carry, `Δ = xT[end_cell] − xT[start_cell]` (net; backward moves count negative).
- **Metrics:** `xt` (Σ Δ over passes + carries), `xt_pass`, `xt_carry`. per-90.
- **Validation:** value surface rises toward goal; per-match team xT tracks team npxG; cross-check the surface shape against a published grid as an external reference.

#### 8.4.2 xGChain / xGBuildup — npxG basis

Possession-involvement metrics (full per-possession definition in working notes). WhoScored carries **no possession marker**, so possessions are segmented from the event stream.

- **Segmentation:** events chunked into single-team possessions. A possession ends on a shot, a dead-ball (ball out, foul awarded, offside, goal, period end, substitution), or when the opponent establishes control. **Smoothing:** brief opponent interruptions the team immediately regains (an unsuccessful opponent touch / block / clearance recovered on the next action) do *not* end the possession — without this, chains are under-credited (median involvement collapses to ~2; target ~3–4).
- **Possession value `V`:** the highest **non-penalty** xG among shots in that possession.
- **npxGChain:** every player with ≥1 on-ball touch in a shot-ending possession `+= V`, once per possession.
- **npxGBuildup:** as above, excluding the shooter and the assister (the pass immediately preceding the shot).
- Penalties excluded (npxG basis); set-piece possessions included.
- **Metrics:** `xg_chain`, `xg_buildup`. per-90.
- **Validation:** per-possession credit reconciles to `V`; team totals track team npxG.

#### 8.4.3 Known limitations

- WhoScored does not flag whether a tackle was against a dribbler, so FBref's "dribblers tackled %" split is **not reproducible** — we expose **Tackle win %** and **Times dribbled past** instead.
- Carry-derived metrics inherit the §8.3 carry-stitching heuristic.
- xGChain/xGBuildup over-credit players on possession-dominant teams and deep recyclers (a keeper recycling in a long build-up is credited); read them as **involvement**, not value-added.

## 9. Comparison pool and percentile rules

- **Pool definition**: same competition + same season + same position bucket.
- **Minutes threshold**: configurable. Default = 30% of total possible minutes in that competition × season (e.g. Premier League 2025–26 = 38 matches × 90 min × 30% = 1,026 min). Configurable per-position if needed.
- **Percentile method**: `PERCENT_RANK()` window function in Postgres, partitioned by `(season_id, position_bucket)`. Equivalent to FBref's "average of % strictly below and % at-or-equal" within rounding tolerance.
- **Lower-is-better stats**: there are none in our outfield stat list. (For goalkeepers later, goals-conceded etc. would need inversion.)

### Implementation as a SQL view

```sql
CREATE OR REPLACE VIEW player_season_percentiles AS
SELECT
  pss.player_id,
  pss.season_id,
  pss.position_bucket,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.npxg_p90) * 100 AS npxg_p90_pct,
  PERCENT_RANK() OVER (PARTITION BY pss.season_id, pss.position_bucket ORDER BY pss.progressive_passes_p90) * 100 AS progressive_passes_p90_pct,
  -- ... one column per stat
  pss.minutes
FROM player_season_stats pss
WHERE pss.minutes >= (
  SELECT minutes_threshold
  FROM percentile_config
  WHERE season_id = pss.season_id
);
```

A separate `percentile_config` table holds the threshold per season/competition for tweakability.

## 10. Frontend

### Pages

1. **Home / search** — search players by name; filter by competition + season; recent players list
2. **Player profile** — player header (photo if available, team, position, age), then scouting section
3. **Scouting section** (the FBref-style centrepiece)
   - Filter selector: which competition + season pool to compare against
   - Percentile bar list (FBref-style): one bar per stat, raw value on the left, bar in middle, percentile number on right
   - Bars colour-coded by category (attack, passing, possession, defence) — same colour scheme as FBref
4. **Comparison page** — two players overlaid on a radar chart + side-by-side percentile bars

### UI direction

- Modern, clean typography (not FBref's dense tabular look)
- Generous whitespace, large player header
- FBref-style percentile bars retained as the recognisable centrepiece
- No branding, no watermark, no logo, no URL header — so screenshots are anonymous by default

### Tech notes

- Use server components for the scouting section (data is static per-request); client components only where interactivity is needed (filter dropdowns, comparison search)
- Tailwind for styling; shadcn/ui components OK if needed
- Radar chart: recharts `RadarChart` or d3 custom — pick whichever is easier

## 11. Phased build with validation gates

**Each phase ends with a validation step. Do not proceed to the next phase until the validation passes and the user has reviewed it.**

### Phase 0 — Scaffolding (1 evening)
- Create new GitHub repo with `/scraper` (Python) and `/web` (Next.js) directories
- Create new Supabase project (separate from the plant DB)
- Configure secrets in GitHub Actions: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
- Configure Vercel project pointing at `/web`
- `.env.local` template committed (without secrets)
- **Validation**: empty repo deploys to Vercel without errors; can connect to Supabase from a test script

### Phase 1 — Single-match scraper (highest risk)
- Python + Playwright scraping one WhoScored match URL
- Extract `matchCentreData` JSON from the embedded `<script>` tag
- Save raw JSON to disk
- **Verify coordinate orientation** empirically: scrape a known match, parse a known player's shot locations, confirm they appear in the attacking half from that team's perspective
- **Validation**: run against Arsenal's most recent home match; print parsed event count and Saka's pass count; user verifies the pass count matches what WhoScored displays in its UI for that match

### Phase 2 — Schema + storage setup
- Run all schema migrations on Supabase
- Set up Supabase Storage bucket `raw-matches` with appropriate access policies (private, service role only)
- Insert seed rows for the 8 competitions
- **Validation**: schema visible in Supabase dashboard; service role can upload/download a test JSON to Storage

### Phase 3 — Computation layer
- Implement all 23 stat-tagging functions in Python
- Implement match-level aggregation (events → player_match_stats)
- Implement season-level aggregation (player_match_stats → player_season_stats, with per-90 conversion and position assignment)
- Unit tests for each stat tagger against hand-checked match excerpts
- **Validation**: ingest one finished Arsenal match end-to-end; user inspects Saka's row in `player_match_stats` and verifies plausible numbers vs publicly known stats

### Phase 4 — Fixture discovery + idempotent backfill
- Script to discover all match URLs for a competition + season from WhoScored fixtures pages
- Backfill orchestrator: queues matches, scrapes, ingests, uploads JSON to Storage, marks complete
- Idempotent: re-running skips already-ingested matches
- Resumable: can be interrupted and restarted
- Rate-limited: configurable delay between matches (default 30s)
- **Validation**: backfill the full Premier League 2025–26 season (current). User inspects the Arsenal squad's stats and confirms they look plausible vs publicly known. **Backfill the remaining ~7,500 matches on user's Mac, running in background. May take 3–5 days.**

### Phase 5 — Scheduled daily scraper
- GitHub Actions workflow on cron (02:00 UTC daily)
- Detects matches where `status='scheduled'` and kickoff was > 4 hours ago → re-scrapes them
- Detects new fixtures and inserts them
- Failure notification: GitHub Actions email + optional Discord/Telegram webhook
- **Validation**: schedule fires successfully two days in a row; new matches appear in the DB without user intervention

### Phase 6 — Percentile engine
- Implement `player_season_percentiles` view
- Implement `percentile_config` table with sensible defaults
- **Validation**: query for any forward in PL 2025–26; user spot-checks a few percentile values for plausibility against intuition (e.g. Haaland should be ~99th percentile for goals)

### Phase 7 — API layer
- Next.js API routes (or Supabase RPC):
  - `GET /api/players/search?q=...`
  - `GET /api/players/[id]/scouting-report?season=...&competition=...`
  - `GET /api/players/compare?id1=...&id2=...&season=...`
- Type-safe responses (zod or just TypeScript interfaces)
- **Validation**: hit each endpoint with curl/Postman; responses are well-formed

### Phase 8 — Frontend
- Home / player search
- Player profile page with scouting section
- Comparison page
- **Validation**: user can search for any in-scope player, see their scouting report, compare two players, all without errors

### Phase 9 — Polish + docs
- Caching (revalidate on data refresh, not per-request)
- Loading states, error boundaries
- Mobile layout review
- `MAINTENANCE.md` — see section 13 below
- **Validation**: user can return in a week, find the dashboard up-to-date, navigate without bugs

### Phase 10 (deferred) — Goalkeeper scouting reports
- Own stat list (saves, PSxG, cross stopping, distribution accuracy, sweeping actions)
- Separate UI variant for GK profile pages
- Not part of v1

### Phase 11 (deferred) — Event-level features
- Pass maps, shot maps, heatmaps
- Requires migration to Postgres event-store (upgrade to Supabase Pro, ~€25/month)
- Re-parse JSONs from Storage into an `events` table
- Not part of v1

## 12. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| WhoScored Cloudflare blocks the scraper | High | High | Stealth Playwright (`playwright-stealth` or `undetected-playwright`), low rate (30s/match), residential IP. If GitHub Actions IP gets blocked: move daily cron to a self-hosted runner on user's Mac or a small VPS. |
| WhoScored changes the page structure / JSON shape | Medium-high | Medium | Single point of parsing: isolate the matchCentreData extractor in one function. When it breaks, user pastes the error + page HTML to Claude in a new chat. Fix scope is small. |
| Coordinate orientation assumption wrong | Medium | High (all progression-based stats are garbage) | Empirical verification in Phase 1. Hard-fail Phase 1 if uncertain. |
| Position classification edge cases (false 9s, inverted FBs) | Medium | Low | Documented as expected; no perfect solution; users of FBref had the same issue. |
| Stat values don't exactly match FBref's published numbers | High | Low | Document our exact definitions in `MAINTENANCE.md`. Spot-check vs other public sources (Sofascore, FotMob) rather than trying to match FBref exactly. |
| Backfill takes longer than expected (Mac sleeps, network drops) | Medium | Low | Idempotent and resumable backfill; user can pause and resume. |
| Supabase free tier limits hit | Low | Medium | Hybrid storage keeps Postgres footprint small. If hit: upgrade or trim historical seasons. |
| Daily GitHub Actions minutes exceed free tier | Low | Low | Daily scrape is ~15 min, well under 2000 min/month free allowance. |

## 13. Maintenance discipline

A `MAINTENANCE.md` file lives in the repo and must be updated whenever:
- The WhoScored scraper is patched
- A stat definition changes
- The schema changes

It must contain:
- Exact CSS/HTML selectors and JSON paths used to extract matchCentreData
- The schema of WhoScored's matchCentreData JSON (as we understand it)
- Each stat's exact definition and the relevant event types/qualifiers used
- A "when the scraper breaks" runbook: how to reproduce locally, what to capture (error trace, page HTML, failing match URL), what to paste into a new Claude chat to get a fix

This is mission-critical because future Claude sessions (whether in chat or Claude Code) won't have the context of this conversation. The doc IS the institutional memory.

## 14. Anti-patterns / things not to do

- **Don't store events in Postgres on free tier.** It blows the 500 MB limit. Hybrid pattern is non-negotiable for v1.
- **Don't add branding / watermarks / URLs to the dashboard UI.** Keeps screenshots anonymous.
- **Don't share the dashboard URL with anyone. Personal use only.**
- **Don't try to match FBref's exact numerical output.** Definitions have drifted over years and our derivation may diverge slightly. Match the methodology, not the digits.
- **Don't hardcode the stat list in the frontend.** Use a config object so adding/removing stats is a one-place change.
- **Don't skip Phase 1 validation.** If the coordinate orientation is wrong, every progression stat is wrong. Catch it before Phase 3.
- **Don't run the full backfill on GitHub Actions.** Use the Mac. Saves Actions minutes for the daily incremental.
- **Don't add Sofascore / FotMob / Understat data alongside WhoScored.** Mixing event-data providers creates inconsistencies. Stick to one source for v1.

## 15. Open questions for future iterations

- Should comparison pools be expandable to "Big-5 combined" or cross-season pools? (Phase 11+)
- Should historical players (transferred out, retired mid-data) still surface in search? (Default: yes, but hide from default rankings)
- Should the dashboard support multiple positions for hybrid players (e.g. a player splitting 60/40 between CM and AM)? (Currently: dominant position wins; revisit if visibly wrong for known hybrids)

---

End of spec. Refer to `CLAUDE.md` for execution conventions.
