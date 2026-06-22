-- Accent-insensitive player search: "Odegaard" finds "Ødegaard", "Muller" finds
-- "Müller", etc. unaccent() folds both the stored name and the query.
CREATE EXTENSION IF NOT EXISTS unaccent;

CREATE OR REPLACE FUNCTION search_players(q text, lim int DEFAULT 20)
RETURNS TABLE (id int, name text)
LANGUAGE sql STABLE
SET search_path = public, extensions
AS $$
  SELECT p.id, p.name
  FROM players p
  WHERE unaccent(lower(p.name)) LIKE '%' || unaccent(lower(q)) || '%'
  ORDER BY p.name
  LIMIT lim;
$$;
