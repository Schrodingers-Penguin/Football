"""Unit tests for fixtures-URL resolution helpers (pure parts, no browser)."""

from src.whoscored.competitions import (
    COMPETITION_REGIONS,
    pick_season_url,
    ws_season_text,
)


def test_ws_season_text_format():
    assert ws_season_text("2024-2025") == "2024/2025"
    assert ws_season_text("2025-2026") == "2025/2026"


def test_pick_season_url_matches_label():
    options = [
        {"value": "/Regions/206/Tournaments/4/Seasons/10803/spain-laliga", "text": "2025/2026"},
        {"value": "/Regions/206/Tournaments/4/Seasons/10317/spain-laliga", "text": "2024/2025"},
        {"value": "/Regions/206/Tournaments/4/Seasons/9682/spain-laliga", "text": "2023/2024"},
    ]
    assert pick_season_url(options, "2024-2025").endswith("/Seasons/10317/spain-laliga")
    assert pick_season_url(options, "2023-2024").endswith("/Seasons/9682/spain-laliga")


def test_pick_season_url_tolerates_whitespace():
    options = [{"value": "/x/10316", "text": "  2024/2025 "}]
    assert pick_season_url(options, "2024-2025") == "/x/10316"


def test_pick_season_url_missing_returns_none():
    options = [{"value": "/x/1", "text": "2019/2020"}]
    assert pick_season_url(options, "2024-2025") is None


def test_champions_league_excluded_from_region_map():
    # CL (12) is multi-stage and intentionally not auto-resolvable here.
    assert 12 not in COMPETITION_REGIONS
    assert set(COMPETITION_REGIONS) == {2, 3, 4, 5, 13, 21, 22}
