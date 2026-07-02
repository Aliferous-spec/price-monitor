"""
Price Monitor — main entry point.

Periodically scrapes a product page, logs the price, and sends alerts
when the price drops below a configured threshold or hits a new low.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Bootstrap: allow `python main.py` to work from the project root
# ---------------------------------------------------------------------------
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

# ---------------------------------------------------------------------------
# Optional .env support — load before reading config
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_here, ".env"))
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Project modules
# ---------------------------------------------------------------------------
from scraper import get_current_price
from storage import PriceRecord, save_record, price_dropped, get_lowest_price
from notifier import notify, NOTIFIERS

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def _load_config() -> dict:
    """Load configuration from ``config.py``, falling back to env vars.

    ``config.py`` is the preferred source; any key that is also set as an
    environment variable will be overridden by the env var.
    """
    config: dict = {}

    # 1. Try to import config.py
    try:
        import config as cfg_mod

        for key in dir(cfg_mod):
            if key.isupper():
                config[key] = getattr(cfg_mod, key)
        logging.debug("Loaded %d keys from config.py", len(config))
    except ImportError:
        logging.warning("config.py not found — using environment variables only")

    # 2. Overlay environment variables (higher priority)
    for key in (
        "TARGET_URL",
        "CSS_SELECTOR",
        "PRICE_REGEX",
        "CHECK_INTERVAL",
        "PRICE_THRESHOLD",
        "EMAIL_RECIPIENT",
        "SMTP_SERVER",
        "SMTP_PORT",
        "SMTP_USER",
        "SMTP_PASSWORD",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
    ):
        env_val = os.getenv(key)
        if env_val is not None:
            config[key] = env_val

    return config


def _validate_config(config: dict) -> None:
    """Exit early if required keys are missing."""
    required = ["TARGET_URL", "CSS_SELECTOR"]
    missing = [k for k in required if not config.get(k)]
    if missing:
        logging.error(
            "Missing required config key(s): %s\n"
            "Copy config.example.py → config.py and fill in the values.",
            ", ".join(missing),
        )
        sys.exit(1)

    # Normalise numeric config
    config.setdefault("CHECK_INTERVAL", 3600)
    config.setdefault("PRICE_THRESHOLD", float("inf"))
    try:
        config["CHECK_INTERVAL"] = int(config["CHECK_INTERVAL"])
        config["PRICE_THRESHOLD"] = float(config["PRICE_THRESHOLD"])
    except (TypeError, ValueError) as exc:
        logging.error("Invalid numeric config value: %s", exc)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def _build_alert_body(price: float, threshold: float, lowest: float | None) -> str:
    lines = [
        f"当前价格: ¥{price:.2f}",
        f"设定阈值: ¥{threshold:.2f}",
    ]
    if lowest is not None:
        lines.append(f"历史最低: ¥{lowest:.2f}")
    return "\n".join(lines)


def check_once(config: dict) -> PriceRecord | None:
    """Run one scrape→save→alert cycle.  Returns the new record, or None on failure."""
    url = config["TARGET_URL"]
    selector = config["CSS_SELECTOR"]
    regex = config.get("PRICE_REGEX")
    threshold = config["PRICE_THRESHOLD"]
    history_file = config.get("HISTORY_FILE", "price_history.jsonl")

    # 1. Scrape
    price = get_current_price(url, selector, regex=regex)
    if price is None:
        logging.warning("Could not extract price — skipping this cycle")
        return None

    # 2. Persist
    record = PriceRecord(
        timestamp=datetime.now(timezone.utc).isoformat(),
        url=url,
        price=price,
    )
    save_record(record, filepath=history_file)

    # 3. Decide whether to alert
    should_alert = False
    reason = ""

    if price <= threshold:
        should_alert = True
        reason = f"价格 ¥{price:.2f} 低于阈值 ¥{threshold:.2f}"
    elif price_dropped(price, filepath=history_file):
        should_alert = True
        reason = f"价格 ¥{price:.2f} 较上次记录下降"

    if should_alert:
        lowest = get_lowest_price(filepath=history_file)
        lowest_price = lowest.price if lowest else None
        subject = f"🔔 价格提醒: ¥{price:.2f}"
        body = reason + "\n\n" + _build_alert_body(price, threshold, lowest_price)
        notify(config, subject, body)

    return record


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    config = _load_config()
    _validate_config(config)

    interval = config["CHECK_INTERVAL"]
    logging.info(
        "🚀 Price Monitor started — checking %s every %ds",
        config["TARGET_URL"], interval,
    )
    logging.info(
        "   Notifiers enabled: %s",
        ", ".join(NOTIFIERS.keys()) or "(none)",
    )

    try:
        while True:
            check_once(config)
            logging.info("Next check in %ds ...", interval)
            time.sleep(interval)
    except KeyboardInterrupt:
        logging.info("👋 Shutting down. Goodbye!")


if __name__ == "__main__":
    main()
