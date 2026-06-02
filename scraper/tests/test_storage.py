"""Unit tests for storage path + gzip round-trip (no network)."""

from src.storage import compress_match, decompress_match, storage_path


def test_storage_path():
    assert storage_path(2, "2025-2026", 1903405) == "2/2025-2026/1903405.json.gz"


def test_gzip_round_trip():
    md = {"events": [{"x": 1.5, "y": 2.0}], "home": {"teamId": 13}, "unicode": "Gyökeres"}
    blob = compress_match(md)
    assert isinstance(blob, bytes)
    assert decompress_match(blob) == md


def test_gzip_actually_compresses():
    md = {"events": [{"i": i} for i in range(1000)]}
    import json

    raw = json.dumps(md).encode()
    assert len(compress_match(md)) < len(raw)
