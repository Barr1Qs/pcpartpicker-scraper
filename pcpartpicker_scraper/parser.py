"""
HTML parsing module for PCPartPicker product rows.
Extracts component names, prices, ratings, and necessary specifications.
"""

import re
from typing import Any, Dict, List
from bs4 import BeautifulSoup
from .config import CATEGORIES_CONFIG


class ProductParser:
    """Parses raw HTML table rows returned by the category endpoint."""

    @staticmethod
    def parse_rows(html: str, category_key: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        products = []
        spec_keys = CATEGORIES_CONFIG[category_key]["spec_keys"]

        for tr in soup.find_all("tr", class_="tr__product"):
            pid = tr.get("data-pb-id") or tr.get("id", "")

            # Name & URL
            name_el = tr.select_one(".td__name p")
            name = name_el.get_text(strip=True) if name_el else ""

            link_el = tr.select_one(".td__name a")
            url = ""
            if link_el and link_el.has_attr("href"):
                href = link_el["href"]
                url = f"https://pcpartpicker.com{href}" if href.startswith("/") else href

            # Price
            price_el = tr.select_one(".td__price")
            price = ""
            if price_el:
                for sub in price_el.select("button, a"):
                    sub.decompose()
                price = price_el.get_text(strip=True)

            # Rating
            rating_el = tr.select_one(".td__rating")
            rating_str = ""
            rating_count = 0
            if rating_el:
                r_text = rating_el.get_text(strip=True)
                match = re.search(r"\((\d+)\)", r_text)
                if match:
                    rating_count = int(match.group(1))
                rating_str = r_text

            # Specifications
            raw_specs: Dict[str, str] = {}
            for s in tr.select(".td__spec"):
                lbl = s.select_one(".specLabel")
                if lbl:
                    label_text = lbl.get_text(strip=True)
                    lbl.decompose()
                    raw_specs[label_text] = s.get_text(strip=True)

            # Extract necessary specifications in consistent order
            specs: Dict[str, str] = {}
            for k in spec_keys:
                specs[k] = raw_specs.get(k, "")
            # Include any other specs present
            for k, v in raw_specs.items():
                if k not in specs:
                    specs[k] = v

            products.append({
                "id": pid,
                "category": category_key,
                "name": name,
                "price": price,
                "rating": rating_str,
                "rating_count": rating_count,
                "url": url,
                "specs": specs,
            })

        return products
