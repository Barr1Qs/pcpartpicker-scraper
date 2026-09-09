"""
Main Scraping Orchestrator for PCPartPicker.
Coordinates category iteration, in-page hash navigation, retries, and storage.
"""

import asyncio
import logging
import math
import random
from pathlib import Path
from typing import List, Optional
from playwright.async_api import BrowserContext, Response

from .browser import BrowserManager, solve_cloudflare_challenge
from .config import (
    CATEGORIES_CONFIG,
    DEFAULT_DELAY_MAX,
    DEFAULT_DELAY_MIN,
    DEFAULT_OUTPUT_DIR,
)
from .parser import ProductParser
from .storage import DataExporter, StateManager

logger = logging.getLogger("pcpp_scraper.orchestrator")


class PCPartPickerScraper:
    """High-level scraper engine for PCPartPicker component catalogs."""

    def __init__(
        self,
        output_dir: str = DEFAULT_OUTPUT_DIR,
        delay_min: float = DEFAULT_DELAY_MIN,
        delay_max: float = DEFAULT_DELAY_MAX,
        headless: bool = False,
        profile_dir: Optional[str] = None,
        categories: Optional[List[str]] = None,
        max_pages: Optional[int] = None,
        resume: bool = True,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.headless = headless
        self.profile_dir = Path(profile_dir) if profile_dir else self.output_dir / "browser_profile"
        self.categories = categories or list(CATEGORIES_CONFIG.keys())
        self.max_pages = max_pages
        self.resume = resume

        self.state_mgr = StateManager(self.output_dir / "scraper_state.json")
        self.exporter = DataExporter(self.output_dir)

    async def scrape_category(self, context: BrowserContext, category_key: str):
        config = CATEGORIES_CONFIG[category_key]
        cat_name = config["name"]
        cat_url = config["url"]

        logger.info(f"\n{"="*60}\nStarting category: {cat_name} ({cat_url})\n{"="*60}")

        page = context.pages[0] if context.pages else await context.new_page()

        # Intercept initial catalog data
        initial_future = asyncio.Future()

        def handle_initial(response: Response):
            if "category" in response.url and not initial_future.done():
                try:
                    initial_future.set_result(response)
                except Exception:
                    pass

        page.on("response", handle_initial)
        logger.info(f"Loading base catalog page: {cat_url}")
        await page.goto(cat_url, wait_until="domcontentloaded", timeout=45000)

        passed = await solve_cloudflare_challenge(page)
        if not passed:
            logger.error(f"Failed to clear Cloudflare challenge for {cat_name}. Skipping...")
            page.remove_listener("response", handle_initial)
            return

        try:
            resp = await asyncio.wait_for(initial_future, timeout=20)
        except asyncio.TimeoutError:
            logger.info("Awaiting initial response after challenge transition...")
            await page.evaluate('window.location.hash = "#page=1"')
            resp = await asyncio.wait_for(initial_future, timeout=20)

        data = await resp.json()
        total_items = data.get("count", 0)
        total_pages = math.ceil(total_items / 100) if total_items > 0 else 1
        logger.info(f"{cat_name} metadata: {total_items} total items, ~{total_pages} pages")
        self.state_mgr.set_meta(category_key, total_items, total_pages)

        page.remove_listener("response", handle_initial)

        # Parse and save page 1
        if not (self.resume and self.state_mgr.is_page_done(category_key, 1)):
            p1_products = ProductParser.parse_rows(data.get("html", ""), category_key)
            self.exporter.append_jsonl(category_key, p1_products)
            self.state_mgr.mark_page_done(category_key, 1)
            logger.info(f"Page 1/{total_pages}: saved {len(p1_products)} products")
        else:
            logger.info(f"Page 1/{total_pages}: already completed (resumed)")

        # Determine remaining pages to scrape
        target_max = min(total_pages, self.max_pages) if self.max_pages else total_pages
        pages_to_scrape = range(2, target_max + 1)

        for target_page in pages_to_scrape:
            if self.resume and self.state_mgr.is_page_done(category_key, target_page):
                logger.info(f"Page {target_page}/{total_pages}: already completed, skipping.")
                continue

            sleep_time = random.uniform(self.delay_min, self.delay_max)
            await asyncio.sleep(sleep_time)

            retry_count = 0
            max_retries = 3
            success = False

            while retry_count < max_retries and not success:
                page_future = asyncio.Future()

                def handle_page_response(response: Response, p_num=target_page, fut=page_future):
                    if "category" in response.url and not fut.done():
                        post_data = response.request.post_data or ""
                        if f"page={p_num}" in post_data:
                            try:
                                fut.set_result(response)
                            except Exception:
                                pass

                page.on("response", handle_page_response)

                try:
                    await page.evaluate(f'window.location.hash = "#page={target_page}"')
                    resp = await asyncio.wait_for(page_future, timeout=20)
                    page_data = await resp.json()
                    products = ProductParser.parse_rows(page_data.get("html", ""), category_key)

                    self.exporter.append_jsonl(category_key, products)
                    self.state_mgr.mark_page_done(category_key, target_page)
                    logger.info(
                        f"Page {target_page}/{total_pages}: parsed & saved {len(products)} products "
                        f"({len(self.state_mgr.get_completed_pages(category_key))}/{total_pages} done)"
                    )
                    success = True
                except asyncio.TimeoutError:
                    retry_count += 1
                    logger.warning(
                        f"Timeout waiting for page {target_page} response (attempt {retry_count}/{max_retries})"
                    )
                    await solve_cloudflare_challenge(page, max_wait=10)
                    await page.evaluate(f'window.location.hash = "#page={target_page - 1}"')
                    await asyncio.sleep(2)
                except Exception as e:
                    retry_count += 1
                    logger.error(f"Error on page {target_page}: {e} (attempt {retry_count}/{max_retries})")
                    await asyncio.sleep(3)
                finally:
                    page.remove_listener("response", handle_page_response)

            if not success:
                logger.error(f"Failed to scrape page {target_page} after {max_retries} attempts.")

        # Batch export clean JSON and CSV
        self.exporter.export_all_formats(category_key)

    async def run(self):
        logger.info(f"Target categories: {', '.join(self.categories)}")
        browser_mgr = BrowserManager(self.profile_dir, headless=self.headless)

        async with browser_mgr as context:
            for cat in self.categories:
                if cat not in CATEGORIES_CONFIG:
                    logger.warning(f"Unknown category '{cat}'. Allowed: {list(CATEGORIES_CONFIG.keys())}")
                    continue
                await self.scrape_category(context, cat)
                await asyncio.sleep(2)

            logger.info(f"\nAll scraping finished! Exported files are located in: {self.output_dir.resolve()}")
