"""
Storage module — persists price records to disk and provides history queries.

Uses a JSON-lines file (one JSON object per line) for simplicity:
- Human-readable.
- Append-only writes are safe without locking for our single-writer use case.
- Easy to inspect with any text editor.
"""

from __future__ import annotations

import json
import os
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class PriceRecord:
    """A single price observation."""

    timestamp: str       # ISO-8601, UTC
    url: str
    price: float
    currency: str = "CNY"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def save_record(record: PriceRecord, filepath: str = "price_history.jsonl") -> None:
    """Append a single price record to the history file (JSON-lines)."""
    _ensure_dir(filepath)
    line = json.dumps(asdict(record), ensure_ascii=False)
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    logger.info("Saved: ¥%.2f @ %s", record.price, record.timestamp)


def load_history(filepath: str = "price_history.jsonl") -> List[PriceRecord]:
    """Read all price records from the history file.

    Returns an empty list if the file does not exist.
    """
    if not os.path.isfile(filepath):
        logger.debug("History file %r not found; returning empty list", filepath)
        return []

    records: List[PriceRecord] = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                records.append(PriceRecord(**obj))
            except (json.JSONDecodeError, TypeError) as exc:
                logger.warning("Skipping corrupt line in history: %s", exc)
    return records


def get_lowest_price(filepath: str = "price_history.jsonl") -> Optional[PriceRecord]:
    """Return the record with the lowest price in history, or None."""
    records = load_history(filepath)
    if not records:
        return None
    return min(records, key=lambda r: r.price)


def get_current_price_record(filepath: str = "price_history.jsonl") -> Optional[PriceRecord]:
    """Return the most recent price record, or None."""
    records = load_history(filepath)
    return records[-1] if records else None


def price_dropped(
    new_price: float,
    filepath: str = "price_history.jsonl",
) -> bool:
    """Return True if *new_price* is strictly lower than the last recorded price."""
    last = get_current_price_record(filepath)
    if last is None:
        return False
    return new_price < last.price


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _ensure_dir(filepath: str) -> None:
    d = os.path.dirname(filepath)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
