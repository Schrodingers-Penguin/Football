-- Player age, recovered from WhoScored matchCentreData.
--
-- matchCentreData carries an integer `age` per player, but it is the player's age
-- AT SCRAPE TIME, not at kickoff: a 2023-08-12 match ingested in June 2026 reports
-- Ramsdale as 28 (his June-2026 age), not the 25 he was that day. So age cannot be
-- paired with kickoff, and birth_date cannot be derived to better than a ~1-year
-- window — the whole backfill was ingested inside a 6-day span, so every
-- observation of a player yields nearly the same constraint.
--
-- What IS exact is the age on the observation date. Store that, plus the date it
-- was observed, rather than fabricating a birth_date accurate to ±6 months.
-- players.birth_date stays NULL: WhoScored's match feed cannot fill it honestly.
--
-- age_as_of lets the UI age a player forward (or flag the value as stale) instead
-- of silently treating a 2026 observation as current.

ALTER TABLE players ADD COLUMN IF NOT EXISTS age INT;
ALTER TABLE players ADD COLUMN IF NOT EXISTS age_as_of DATE;

COMMENT ON COLUMN players.age IS
  'Age in years as reported by WhoScored on age_as_of. Exact on that date; not a birth-date derivation.';
COMMENT ON COLUMN players.age_as_of IS
  'Date the age was observed (the match scrape date, not the kickoff).';

CREATE INDEX IF NOT EXISTS players_age_idx ON players (age);
