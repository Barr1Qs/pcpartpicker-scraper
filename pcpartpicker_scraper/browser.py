"""
Browser management module.
Handles persistent contexts, Chromium detection, and Cloudflare Turnstile bypass.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional
from playwright.async_api import BrowserContext, Page, async_playwright
from .config import DEFAULT_VIEWPORT

logger = logging.getLogger("pcpp_scraper.browser")


def find_system_chromium() -> Optional[str]:
    """Locates installed Chromium / Chrome executable on the system."""
    candidates = [
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/google-chrome",
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


async def solve_cloudflare_challenge(page: Page, max_wait: int = 20) -> bool:
    """
    Checks if a Cloudflare Turnstile challenge is present and attempts auto-resolution.
    Uses coordinate clicking on the challenge iframe to avoid shadow DOM blocking.
    """
    for sec in range(max_wait):
        title = await page.title()
        if "Just a moment" not in title:
            return True

        if sec == 0:
            logger.info("Cloudflare challenge page detected. Waiting for verification...")

        await asyncio.sleep(1)

        # Attempt to locate the Turnstile widget iframe and click its checkbox area
        try:
            iframe = await page.query_selector("iframe[src*='challenges.cloudflare.com']")
            if iframe:
                box = await iframe.bounding_box()
                if box:
                    click_x = box["x"] + 30
                    click_y = box["y"] + (box["height"] / 2)
                    await page.mouse.click(click_x, click_y)
                    await asyncio.sleep(1.5)
        except Exception:
            pass

    final_title = await page.title()
    return "Just a moment" not in final_title


class BrowserManager:
    """Manages persistent Playwright browser contexts."""

    def __init__(self, profile_dir: Path, headless: bool = False):
        self.profile_dir = profile_dir
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.playwright = None
        self.context: Optional[BrowserContext] = None

    async def __aenter__(self) -> BrowserContext:
        self.playwright = await async_playwright().start()
        exec_path = find_system_chromium()
        logger.info(f"Using Chromium binary: {exec_path or "Playwright bundled Chromium"}")
        logger.info(f"Using persistent profile: {self.profile_dir}")

        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_dir),
            executable_path=exec_path,
            headless=self.headless,
            viewport=DEFAULT_VIEWPORT,
            args=["--disable-blink-features=AutomationControlled"],
        )
        return self.context

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
