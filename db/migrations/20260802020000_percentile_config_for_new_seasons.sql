-- Why: percentile_config was populated once, by 20260607010000_v2_percentiles,
-- for the seasons that existed then. Nothing populates it for a season created
-- later. get_or_create_season() (scraper/src/ingest/writers.py) inserts the
-- seasons row during the first daily run of a new season, and from that moment:
--
--   * player_season_percentiles filters on
--       pss.minutes >= (SELECT minutes_threshold FROM percentile_config
--                       WHERE season_id = pss.season_id)
--     which is NULL for the new season -> the predicate is never true -> no
--     percentile rows at all;
--   * web/lib/queries.ts falls back to `threshold = +Infinity` when the config
--     row is missing, so the below-threshold comparison pool is empty too.
--
-- Net effect: the 2026-2027 season would have produced a dashboard with no
-- percentiles and no rankings, and nothing would have errored. Fixed with a
-- trigger so the row exists for any season, however it gets created.

-- 30% of a full season's minutes (SPEC §9). 38-match leagues (Premier League=2,
-- La Liga=4, Serie A=5): 38*90*0.3 = 1026. Everything else is an 18-team,
-- 34-match league: 34*90*0.3 = 918. These are the same values 20260607010000
-- seeded; keep the two in step if a competition is ever added.
--
-- An unknown competition falls through to 918 rather than raising: a threshold
-- that is slightly too low shows a diluted pool, one that is too high shows an
-- empty page, and a raise here would block match ingest entirely.
CREATE OR REPLACE FUNCTION default_minutes_threshold(p_competition_id INT)
RETURNS INT LANGUAGE sql IMMUTABLE AS $$
  SELECT CASE WHEN p_competition_id IN (2, 4, 5) THEN 1026 ELSE 918 END;
$$;

CREATE OR REPLACE FUNCTION seed_percentile_config() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  INSERT INTO percentile_config (season_id, minutes_threshold)
  VALUES (NEW.id, default_minutes_threshold(NEW.competition_id))
  ON CONFLICT (season_id) DO NOTHING;  -- never overwrite a hand-tuned threshold
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS seasons_seed_percentile_config ON seasons;
CREATE TRIGGER seasons_seed_percentile_config
AFTER INSERT ON seasons
FOR EACH ROW EXECUTE FUNCTION seed_percentile_config();

-- Backfill: any season that predates the trigger and has no config row.
-- (All 21 current seasons have one; this is here so the migration is complete
-- on its own rather than relying on that.)
INSERT INTO percentile_config (season_id, minutes_threshold)
SELECT s.id, default_minutes_threshold(s.competition_id)
FROM seasons s
WHERE NOT EXISTS (SELECT 1 FROM percentile_config pc WHERE pc.season_id = s.id)
ON CONFLICT (season_id) DO NOTHING;

-- New functions must appear in PostgREST's schema cache before the scraper can
-- call them. Supabase reloads on DDL automatically; this makes it deterministic.
NOTIFY pgrst, 'reload schema';
