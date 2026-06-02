"""Resolve a season's fixtures URL from competition id + season label, with no
hand-maintained URL list.

region/tournament are stable per competition (verified against WhoScored page
titles on 2026-06-02). The season id and stage id are *not* stable and are
discovered live: load the tournament seed, read the season dropdown to find the
season's page, then read that page's "Fixtures" link — which carries the full
`/seasons/<id>/stages/<id>/fixtures/<slug>` path the discoverer needs.

Champions League (id 12) is intentionally excluded: it has multiple stages
(group/league phase + knockouts) so a single fixtures URL is insufficient. Build
it separately.
"""

import asyncio

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

_BASE = "https://www.whoscored.com"

# competitions.id (== WhoScored tournament id) -> WhoScored region id.
# Verified by loading https://www.whoscored.com/Regions/<r>/Tournaments/<t>/ and
# confirming the page title names the competition.
COMPETITION_REGIONS: dict[int, int] = {
    2: 252,   # Premier League — England
    3: 81,    # Bundesliga — Germany
    4: 206,   # La Liga — Spain
    5: 108,   # Serie A — Italy
    13: 155,  # Eredivisie — Netherlands
    21: 177,  # Primeira Liga — Portugal
    22: 74,   # Ligue 1 — France
    # 12: 250 — Champions League: multi-stage, resolve separately (see module docstring)
}

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_STEALTH = Stealth(navigator_platform_override="MacIntel", navigator_user_agent_override=_UA)


def ws_season_text(season_label: str) -> str:
    """Our season label -> WhoScored's dropdown label. '2024-2025' -> '2024/2025'."""
    return season_label.replace("-", "/")


def pick_season_url(options: list[dict], season_label: str) -> str | None:
    """From `#seasons` option dicts ({'value','text'}), the href whose label
    matches the wanted season, else None."""
    want = ws_season_text(season_label)
    for o in options:
        if (o.get("text") or "").strip() == want:
            return o.get("value")
    return None


def _abs(href: str) -> str:
    return href if href.startswith("http") else _BASE + href


async def discover_season_fixtures_url_async(
    competition_id: int, season_label: str, *, headless: bool = True, settle: float = 5.0
) -> str | None:
    """Full fixtures URL (with stage) for a competition+season, or None if the
    season isn't listed. Raises ValueError for competitions without a region map."""
    region = COMPETITION_REGIONS.get(competition_id)
    if region is None:
        raise ValueError(
            f"no region mapping for competition {competition_id} "
            "(Champions League and other multi-stage comps must be resolved separately)"
        )

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            channel="chromium",
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            ctx = await browser.new_context(
                user_agent=_UA,
                viewport={"width": 1280, "height": 900},
                locale="en-GB",
                timezone_id="Europe/London",
            )
            page = await ctx.new_page()
            await _STEALTH.apply_stealth_async(page)

            seed = f"{_BASE}/Regions/{region}/Tournaments/{competition_id}/"
            await page.goto(seed, wait_until="domcontentloaded", timeout=60_000)
            await asyncio.sleep(settle)

            options = await page.evaluate(
                "() => { const s = document.getElementById('seasons');"
                " return s ? [...s.options].map(o => ({value:o.value, text:o.text})) : []; }"
            )
            season_url = pick_season_url(options, season_label)
            if not season_url:
                return None

            await page.goto(_abs(season_url), wait_until="domcontentloaded", timeout=60_000)
            await asyncio.sleep(settle)

            href = await page.evaluate(
                "() => { const a = document.querySelector(\"a[href*='/Fixtures/' i]\");"
                " return a ? a.getAttribute('href') : null; }"
            )
            return _abs(href) if href else None
        finally:
            await browser.close()


def discover_season_fixtures_url(
    competition_id: int, season_label: str, *, headless: bool = True
) -> str | None:
    """Sync wrapper around discover_season_fixtures_url_async."""
    return asyncio.run(
        discover_season_fixtures_url_async(competition_id, season_label, headless=headless)
    )
