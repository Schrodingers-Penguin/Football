"""Fixture discovery: enumerate all match URLs for a competition+season from a
WhoScored fixtures page.

WhoScored shows fixtures one month at a time, loaded dynamically, behind a sticky
overlay that intercepts real mouse clicks. So we drive it with the browser but
page backwards via a JavaScript click on the stable `#dayChangeBtn-prev` control,
scraping `/matches/{id}` links from the DOM at each month until we page past the
season start (two consecutive empty months).

The fixtures URL embeds region/tournament/season/stage, e.g. PL 2025-26:
  /regions/252/tournaments/2/seasons/10743/stages/24533/fixtures/england-premier-league-2025-2026
"""

import asyncio
import re

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from ..ingest.backfill import Fixture

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_STEALTH = Stealth(navigator_platform_override="MacIntel", navigator_user_agent_override=_UA)
_BASE = "https://www.whoscored.com"
_MATCH_RE = re.compile(r"/matches/(\d+)", re.I)
_PREV_CLICK = (
    "() => { const b = document.getElementById('dayChangeBtn-prev');"
    " if (b) { b.click(); return true; } return false; }"
)


async def _collect(page) -> dict[int, str]:
    """match_id -> href for every /matches/ link currently in the DOM."""
    hrefs = await page.eval_on_selector_all(
        "a[href*='/matches/' i]", "els => els.map(e => e.getAttribute('href'))"
    )
    out: dict[int, str] = {}
    for h in hrefs:
        if not h:
            continue
        m = _MATCH_RE.search(h)
        if m:
            out[int(m.group(1))] = h
    return out


async def discover_fixtures_async(
    fixtures_url: str,
    competition_id: int,
    season_label: str,
    *,
    headless: bool = True,
    max_months: int = 15,
    settle: float = 4.0,
) -> list[Fixture]:
    found: dict[int, str] = {}
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
            await page.goto(fixtures_url, wait_until="domcontentloaded", timeout=60_000)
            await asyncio.sleep(7)

            empty_streak = 0
            for _ in range(max_months):
                batch = await _collect(page)
                new = len(set(batch) - set(found))
                found.update(batch)
                if new == 0:
                    empty_streak += 1
                    if empty_streak >= 2:  # paged past the season start
                        break
                else:
                    empty_streak = 0
                if not await page.evaluate(_PREV_CLICK):
                    break
                await asyncio.sleep(settle)
        finally:
            await browser.close()

    return [
        Fixture(
            match_id=mid,
            url=href if href.startswith("http") else _BASE + href,
            competition_id=competition_id,
            season_label=season_label,
        )
        for mid, href in sorted(found.items())
    ]


def discover_fixtures(
    fixtures_url: str,
    competition_id: int,
    season_label: str,
    *,
    headless: bool = True,
) -> list[Fixture]:
    """Sync wrapper around discover_fixtures_async."""
    return asyncio.run(
        discover_fixtures_async(fixtures_url, competition_id, season_label, headless=headless)
    )


# A finished fixture's match link is the score control (class Match-module_score__…,
# text like "31" = 3-1); an unplayed fixture shows a kickoff time instead. Detect
# by class so the daily job only scrapes completed matches, not future fixtures.
# (Class is a CSS-module name — if WhoScored rebuilds and it changes, this is the
#  one selector to update; see MAINTENANCE.)
_FINISHED_SCAN = """() => {
  const out = {};
  document.querySelectorAll("a[href*='/matches/' i][href*='/live' i]").forEach(a => {
    const m = a.getAttribute('href').match(/\\/matches\\/(\\d+)/i);
    if (!m) return;
    const id = m[1];
    const finished = /Match-module_score__/i.test(a.className);
    if (finished || !(id in out)) out[id] = { href: a.getAttribute('href'), finished };
  });
  return Object.entries(out).map(([id, v]) => ({ id: +id, href: v.href, finished: v.finished }));
}"""


async def discover_finished_fixtures_async(
    fixtures_url: str,
    competition_id: int,
    season_label: str,
    *,
    headless: bool = True,
    months: int = 2,
    settle: float = 4.0,
) -> list[Fixture]:
    """Finished fixtures from the current `months` of the calendar (current month
    first, then paging back). Only matches with a score are returned."""
    found: dict[int, str] = {}
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
            await page.goto(fixtures_url, wait_until="domcontentloaded", timeout=60_000)
            await asyncio.sleep(7)

            for _ in range(max(1, months)):
                for item in await page.evaluate(_FINISHED_SCAN):
                    if item["finished"]:
                        found[int(item["id"])] = item["href"]
                if not await page.evaluate(_PREV_CLICK):
                    break
                await asyncio.sleep(settle)
        finally:
            await browser.close()

    return [
        Fixture(
            match_id=mid,
            url=href if href.startswith("http") else _BASE + href,
            competition_id=competition_id,
            season_label=season_label,
        )
        for mid, href in sorted(found.items())
    ]


def discover_finished_fixtures(
    fixtures_url: str,
    competition_id: int,
    season_label: str,
    *,
    headless: bool = True,
    months: int = 2,
) -> list[Fixture]:
    """Sync wrapper around discover_finished_fixtures_async."""
    return asyncio.run(
        discover_finished_fixtures_async(
            fixtures_url, competition_id, season_label, headless=headless, months=months
        )
    )
