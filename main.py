#!/usr/bin/env python3
"""
Main CLI Entry Point for PCPartPicker Scraper.
"""

import argparse
import asyncio
import logging
import sys
from pcpartpicker_scraper.config import (
    CATEGORIES_CONFIG,
    DEFAULT_DELAY_MAX,
    DEFAULT_DELAY_MIN,
    DEFAULT_OUTPUT_DIR,
)
from pcpartpicker_scraper.scraper import PCPartPickerScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="PCPartPicker Full Hardware Scraper (Modular Edition)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--categories",
        nargs="+",
        default=["all"],
        help=f"Categories to scrape. Options: {list(CATEGORIES_CONFIG.keys())} or 'all'",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to save JSON, CSV, JSONL, and state files",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum pages to scrape per category (omit to scrape ALL available pages)",
    )
    parser.add_argument(
        "--delay-min",
        type=float,
        default=DEFAULT_DELAY_MIN,
        help="Minimum delay between requests in seconds",
    )
    parser.add_argument(
        "--delay-max",
        type=float,
        default=DEFAULT_DELAY_MAX,
        help="Maximum delay between requests in seconds",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (default: false for optimal Cloudflare pass)",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Do not resume previous progress; start a fresh scrape",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    cats = list(CATEGORIES_CONFIG.keys()) if "all" in args.categories else args.categories

    scraper = PCPartPickerScraper(
        output_dir=args.output_dir,
        delay_min=args.delay_min,
        delay_max=args.delay_max,
        headless=args.headless,
        categories=cats,
        max_pages=args.max_pages,
        resume=not args.no_resume,
    )
    try:
        asyncio.run(scraper.run())
    except KeyboardInterrupt:
        print("\nScraping paused by user. Progress has been saved and can be resumed anytime.")


if __name__ == "__main__":
    main()
