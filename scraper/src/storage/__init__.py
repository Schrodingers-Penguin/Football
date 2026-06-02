"""Raw match JSON storage in Supabase Storage.

Layout (per SPEC §6):  raw-matches/<competition_id>/<season_label>/<match_id>.json.gz
Verbatim matchCentreData, gzipped. Re-running a metric only needs a re-parse of
these, not a re-scrape.
"""

import gzip
import json

from ..db import get_client

BUCKET = "raw-matches"


def storage_path(competition_id: int, season_label: str, match_id: int) -> str:
    return f"{competition_id}/{season_label}/{match_id}.json.gz"


def compress_match(match_data: dict) -> bytes:
    """Gzip a match dict to bytes (pure; unit-testable without network)."""
    return gzip.compress(json.dumps(match_data, separators=(",", ":")).encode("utf-8"))


def decompress_match(blob: bytes) -> dict:
    """Inverse of compress_match."""
    return json.loads(gzip.decompress(blob))


def upload_raw_match(
    competition_id: int,
    season_label: str,
    match_id: int,
    match_data: dict,
    client=None,
) -> str:
    """Upload gzipped match JSON; return its storage path. Idempotent (upsert)."""
    client = client or get_client()
    path = storage_path(competition_id, season_label, match_id)
    client.storage.from_(BUCKET).upload(
        path,
        compress_match(match_data),
        file_options={"content-type": "application/gzip", "upsert": "true"},
    )
    return path


def download_raw_match(path: str, client=None) -> dict:
    """Download and decompress a stored match by its storage path."""
    client = client or get_client()
    return decompress_match(client.storage.from_(BUCKET).download(path))
