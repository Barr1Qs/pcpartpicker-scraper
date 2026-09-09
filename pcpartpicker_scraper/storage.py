"""
Storage and State Management module.
Handles checkpointing (resumability) and data exports (JSON, CSV, JSONL).
"""

import csv
import json
import logging
from pathlib import Path
from typing import Any, Dict, List
from .config import CATEGORIES_CONFIG

logger = logging.getLogger("pcpp_scraper.storage")


class StateManager:
    """Tracks completed pages per category to allow seamless resumption."""

    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.state: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load state file {self.state_file}: {e}")
        return {}

    def save(self):
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save state: {e}")

    def is_page_done(self, category: str, page_num: int) -> bool:
        cat_state = self.state.get(category, {})
        return page_num in cat_state.get("completed_pages", [])

    def mark_page_done(self, category: str, page_num: int):
        if category not in self.state:
            self.state[category] = {"completed_pages": [], "total_pages": None, "total_items": None}
        if page_num not in self.state[category]["completed_pages"]:
            self.state[category]["completed_pages"].append(page_num)
        self.save()

    def set_meta(self, category: str, total_items: int, total_pages: int):
        if category not in self.state:
            self.state[category] = {"completed_pages": [], "total_pages": None, "total_items": None}
        self.state[category]["total_items"] = total_items
        self.state[category]["total_pages"] = total_pages
        self.save()

    def get_completed_pages(self, category: str) -> List[int]:
        return self.state.get(category, {}).get("completed_pages", [])


class DataExporter:
    """Handles streaming writes to JSONL and batch exports to JSON and CSV."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def append_jsonl(self, category_key: str, items: List[Dict[str, Any]]):
        jsonl_path = self.output_dir / f"{category_key}.jsonl"
        with open(jsonl_path, "a", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

    def export_all_formats(self, category_key: str):
        jsonl_path = self.output_dir / f"{category_key}.jsonl"
        json_path = self.output_dir / f"{category_key}.json"
        csv_path = self.output_dir / f"{category_key}.csv"

        if not jsonl_path.exists():
            return

        items = []
        seen_ids = set()
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    pid = obj.get("id")
                    if pid and pid in seen_ids:
                        continue
                    if pid:
                        seen_ids.add(pid)
                    items.append(obj)
                except Exception:
                    pass

        # Write JSON array
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, ensure_ascii=False)

        # Write CSV with flattened specs
        spec_keys = CATEGORIES_CONFIG[category_key]["spec_keys"]
        fieldnames = ["id", "category", "name", "price", "rating", "rating_count", "url"] + spec_keys

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for item in items:
                row = {
                    "id": item.get("id", ""),
                    "category": item.get("category", ""),
                    "name": item.get("name", ""),
                    "price": item.get("price", ""),
                    "rating": item.get("rating", ""),
                    "rating_count": item.get("rating_count", 0),
                    "url": item.get("url", ""),
                }
                item_specs = item.get("specs", {})
                for k in spec_keys:
                    row[k] = item_specs.get(k, "")
                writer.writerow(row)

        logger.info(f"Exported {len(items)} items to {json_path.name} and {csv_path.name}")
