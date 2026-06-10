"""Unit tests for daily-update helpers (no browser/DB)."""

import datetime as dt

from src.ingest.daily import current_season_label


def test_current_season_label_rolls_over_in_july():
    assert current_season_label(dt.date(2026, 6, 9)) == "2025-2026"  # mid-season
    assert current_season_label(dt.date(2025, 7, 1)) == "2025-2026"  # season start
    assert current_season_label(dt.date(2026, 1, 15)) == "2025-2026"  # new calendar year
    assert current_season_label(dt.date(2025, 6, 30)) == "2024-2025"  # day before rollover
    assert current_season_label(dt.date(2025, 8, 20)) == "2025-2026"
