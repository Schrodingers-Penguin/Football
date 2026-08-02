"""Player age recovery from matchCentreData.

matchCentreData carries an integer `age` per player, but it is the age at SCRAPE
time, not at kickoff — a 2023-08-12 match ingested in June 2026 reports the
player's June-2026 age. Age must therefore be paired with the match's
ingested_at, and no birth date can be derived from it: our whole backfill was
ingested inside a 6-day window, so every observation of a player yields nearly
the same one-year constraint.

What is exact is the age on the observation date, which is what we store.
"""

from collections import Counter

# outside this range the value isn't a plausible senior-squad age and is more
# likely a parsing artefact than a real player
_MIN_AGE = 14
_MAX_AGE = 50


def ages_in_match(match_data: dict, observed_on: str) -> list[tuple[int, str, int]]:
    """(player_id, observed_on, age) for every player in one match's raw JSON."""
    out: list[tuple[int, str, int]] = []
    for side in ("home", "away"):
        for p in match_data.get(side, {}).get("players", []):
            pid, age = p.get("playerId"), p.get("age")
            if pid is None or not isinstance(age, int):
                continue
            if _MIN_AGE <= age <= _MAX_AGE:
                out.append((pid, observed_on, age))
    return out


def resolve_ages(observations: dict) -> tuple[list[dict], Counter]:
    """Collapse each player's {date: age} observations to one (age, age_as_of).

    Takes the newest observation. A player seen with two different ages across
    the scrape window had a birthday inside it, so the later value is current;
    that also makes their age_as_of the most precise one we hold.
    """
    rows: list[dict] = []
    stats: Counter = Counter()
    for pid, by_day in observations.items():
        if not by_day:
            stats["no_observations"] += 1
            continue
        newest = max(by_day)
        rows.append({"id": int(pid), "age": by_day[newest], "age_as_of": newest})
        stats["birthday_in_window" if len(set(by_day.values())) > 1 else "single_age"] += 1
    return rows, stats
