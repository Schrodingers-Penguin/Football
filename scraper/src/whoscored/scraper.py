"""Playwright scraper for WhoScored match pages."""

import asyncio
import json
import random

from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from .extractor import extract_match_centre_data

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_STEALTH = Stealth(
    navigator_platform_override="MacIntel",
    navigator_user_agent_override=_USER_AGENT,
)


async def scrape_match(url: str, headless: bool = False) -> dict:
    """Scrape a WhoScored match page and return the matchCentreData dict.

    headless=False is the default for local use — WhoScored's Cloudflare
    detects headless Chromium more readily than headed.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            context = await browser.new_context(
                user_agent=_USER_AGENT,
                viewport={"width": 1280, "height": 800},
                locale="en-GB",
                timezone_id="Europe/London",
            )
            page = await context.new_page()
            await _STEALTH.apply_stealth_async(page)

            await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            # Brief pause: lets any JS-injected script tags finish rendering.
            await asyncio.sleep(random.uniform(3, 6))

            # Prefer JS evaluation: avoids JSON-invalid values (undefined etc.)
            # that WhoScored embeds in the script tag.
            raw_json = await page.evaluate(
                "() => JSON.stringify(window.require.config.params['args'].matchCentreData)"
            )
            if raw_json:
                return json.loads(raw_json)

            # Fallback: parse from raw HTML string
            html = await page.content()
            return extract_match_centre_data(html)
        finally:
            await browser.close()
