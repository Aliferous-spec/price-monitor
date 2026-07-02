"""
Notifier module — sends price-drop alerts via email and/or Telegram.

Add new channels by implementing a ``send_<channel>(config, subject, body)``
function and registering it in the NOTIFIERS registry at the bottom.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Optional, Callable, Dict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

# A notifier callable receives the full config dict, a subject line, and a
# plain-text body.  It should return ``True`` on success.
NotifierFunc = Callable[[dict, str, str], bool]

NOTIFIERS: Dict[str, NotifierFunc] = {}
"""Registry of available notifiers, keyed by short name (e.g. 'email')."""


# ---------------------------------------------------------------------------
# Decorator for registration
# ---------------------------------------------------------------------------


def register(name: str):
    """Decorator that adds the decorated function to the NOTIFIERS registry."""
    def decorator(fn: NotifierFunc) -> NotifierFunc:
        NOTIFIERS[name] = fn
        return fn
    return decorator


# ---------------------------------------------------------------------------
# Built-in notifiers
# ---------------------------------------------------------------------------


@register("email")
def send_email(config: dict, subject: str, body: str) -> bool:
    """Send an alert via SMTP (Gmail-style).

    Expected config keys
    --------------------
    - EMAIL_RECIPIENT
    - SMTP_SERVER
    - SMTP_PORT
    - SMTP_USER
    - SMTP_PASSWORD
    """
    required = ["EMAIL_RECIPIENT", "SMTP_SERVER", "SMTP_PORT",
                "SMTP_USER", "SMTP_PASSWORD"]
    missing = [k for k in required if not config.get(k)]
    if missing:
        logger.error("Email notifier skipped — missing config: %s", missing)
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config["SMTP_USER"]
    msg["To"] = config["EMAIL_RECIPIENT"]
    msg.set_content(body)

    try:
        server = smtplib.SMTP(config["SMTP_SERVER"], int(config["SMTP_PORT"]))
        server.starttls()
        server.login(config["SMTP_USER"], config["SMTP_PASSWORD"])
        server.send_message(msg)
        server.quit()
        logger.info("Email sent to %s", config["EMAIL_RECIPIENT"])
        return True
    except Exception as exc:
        logger.exception("Failed to send email: %s", exc)
        return False


@register("telegram")
def send_telegram(config: dict, subject: str, body: str) -> bool:
    """Send an alert via a Telegram bot.

    Expected config keys
    --------------------
    - TELEGRAM_BOT_TOKEN
    - TELEGRAM_CHAT_ID
    """
    token = config.get("TELEGRAM_BOT_TOKEN")
    chat_id = config.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        logger.error("Telegram notifier skipped — missing token or chat_id")
        return False

    import requests  # lazy import — requests is already a project dependency

    text = f"*{subject}*\n{body}"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("Telegram message sent to %s", chat_id)
        return True
    except Exception as exc:
        logger.exception("Failed to send Telegram message: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def notify(config: dict, subject: str, body: str) -> dict:
    """Send a notification through every enabled channel.

    Parameters
    ----------
    config : dict
        Application configuration (will be passed to each notifier).
    subject : str
        Alert subject / title.
    body : str
        Alert body (plain text).

    Returns
    -------
    dict
        Mapping of channel name → boolean success indicator.
    """
    results: Dict[str, bool] = {}
    for name, notifier_fn in NOTIFIERS.items():
        logger.debug("Dispatching notifier %r ...", name)
        try:
            results[name] = notifier_fn(config, subject, body)
        except Exception:
            logger.exception("Notifier %r raised an unexpected error", name)
            results[name] = False
    return results
