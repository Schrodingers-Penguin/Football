"""
Phase 2 validation: confirm Storage bucket exists and service role can
upload and download objects.

Usage (from scraper/ directory):
    python scripts/phase2_validate.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from db import get_client

TEST_PATH = "test/phase2_probe.json"
TEST_PAYLOAD = json.dumps({"phase": 2, "status": "ok"}).encode()


def main() -> None:
    client = get_client()
    bucket = "raw-matches"

    # 1. Ensure bucket exists (create if missing)
    existing = [b.name for b in client.storage.list_buckets()]
    if bucket in existing:
        print(f"  ✓ bucket '{bucket}' already exists")
    else:
        client.storage.create_bucket(bucket, options={"public": False})
        print(f"  ✓ bucket '{bucket}' created (private)")

    # 2. Upload test object
    client.storage.from_(bucket).upload(
        TEST_PATH,
        TEST_PAYLOAD,
        file_options={"content-type": "application/json", "upsert": "true"},
    )
    print(f"  ✓ uploaded {TEST_PATH}")

    # 3. Download and verify
    downloaded = client.storage.from_(bucket).download(TEST_PATH)
    assert downloaded == TEST_PAYLOAD, f"Round-trip mismatch: {downloaded!r}"
    print(f"  ✓ downloaded and verified {TEST_PATH}")

    # 4. Clean up
    client.storage.from_(bucket).remove([TEST_PATH])
    print(f"  ✓ cleaned up test object")

    print("\nPhase 2 validation: PASSED")


if __name__ == "__main__":
    main()
