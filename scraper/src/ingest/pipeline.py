"""End-to-end ingestion of one match: matchCentreData -> Postgres + Storage.

Idempotent and resumable: re-running skips a match already marked ingested
(unless force=True). Order of operations matters for FK integrity:
teams/players/season/match must exist before player_match_stats; the raw JSON is
uploaded and the match marked ingested last, so a crash mid-way leaves the match
un-ingested and it will be retried cleanly.
"""

from ..aggregate.match import aggregate_match
from ..db import get_client
from ..parser.events import parse_events
from ..storage import upload_raw_match
from . import writers
from .metadata import extract_match_row, extract_players, extract_teams


def _stat_rows(
    events: list[dict], match_data: dict, match_id: int, season_label: str
) -> list[dict]:
    """player_match_stats rows for every player who appeared, substitutes
    included (position_bucket NULL for subs). Subs' contributions must count
    toward player and team/league totals; the season rollup assigns a player's
    position pool from their bucketed (started) minutes and drops players who
    only ever subbed with no position."""
    return aggregate_match(
        events=events,
        match_data=match_data,
        match_id=match_id,
        competition_id=0,  # unused by aggregate; metadata carries the real ids
        season_label=season_label,
    )


def ingest_match(
    match_data: dict,
    competition_id: int,
    season_label: str,
    match_id: int,
    *,
    client=None,
    force: bool = False,
) -> dict:
    """Ingest one match. Returns a small result dict for logging.

    force=True re-ingests even if already complete.
    """
    client = client or get_client()

    if not force and writers.is_ingested(client, match_id):
        return {"match_id": match_id, "status": "skipped", "reason": "already ingested"}

    season_id = writers.get_or_create_season(client, competition_id, season_label)

    writers.upsert_teams(client, extract_teams(match_data))
    writers.upsert_players(client, extract_players(match_data))
    writers.upsert_match(client, extract_match_row(match_data, match_id, competition_id, season_id))

    events = parse_events(match_data)
    rows = _stat_rows(events, match_data, match_id, season_label)
    writers.upsert_player_match_stats(client, rows)

    raw_path = upload_raw_match(competition_id, season_label, match_id, match_data, client=client)
    writers.mark_ingested(client, match_id, raw_path)

    return {
        "match_id": match_id,
        "status": "ingested",
        "player_rows": len(rows),
        "events": len(events),
        "raw_json_path": raw_path,
    }
