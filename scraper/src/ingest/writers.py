"""Idempotent writes to Supabase Postgres via the service-role client.

All upserts so re-ingesting a match is safe. Conflict targets match the schema's
UNIQUE constraints (SPEC §6).
"""

from datetime import UTC, datetime


def get_or_create_season(client, competition_id: int, season_label: str) -> int:
    """Return seasons.id for (competition, label), creating the row if absent."""
    res = (
        client.table("seasons")
        .upsert(
            {"competition_id": competition_id, "season_label": season_label},
            on_conflict="competition_id,season_label",
        )
        .execute()
    )
    return res.data[0]["id"]


def upsert_teams(client, teams: list[dict]) -> None:
    if teams:
        client.table("teams").upsert(teams).execute()  # conflict on PK id


def upsert_players(client, players: list[dict]) -> None:
    if players:
        client.table("players").upsert(players).execute()  # conflict on PK id


def upsert_match(client, match_row: dict) -> None:
    client.table("matches").upsert(match_row).execute()  # conflict on PK id


def upsert_player_match_stats(client, rows: list[dict]) -> None:
    if rows:
        client.table("player_match_stats").upsert(rows, on_conflict="match_id,player_id").execute()


def mark_ingested(client, match_id: int, raw_json_path: str) -> None:
    client.table("matches").update(
        {"raw_json_path": raw_json_path, "ingested_at": datetime.now(UTC).isoformat()}
    ).eq("id", match_id).execute()


def is_ingested(client, match_id: int) -> bool:
    """True if the match already has a completed ingest (ingested_at set)."""
    res = client.table("matches").select("ingested_at").eq("id", match_id).execute()
    return bool(res.data and res.data[0].get("ingested_at"))
