"""Check the live database matches db/migrations/.

Exits non-zero (listing which migration to apply) if anything is missing.
Migrations are applied by hand in the Supabase SQL editor, so this is the only
thing standing between a skipped file and a silently degraded dashboard.

  python scripts/check_schema.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.schema_check import assert_schema


def main() -> None:
    try:
        assert_schema()
    except RuntimeError as e:
        print(e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
