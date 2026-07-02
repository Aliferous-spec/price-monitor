"""
Price scraper module — fetches web pages and extracts price information.

Supports CSS-selector based extraction with configurable headers,
retry logic, and graceful error handling.
"""

import re
import time
import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = 15  # seconds
DEFAULT_RETRIES = 3
RETRY_BACKOFF = 2  # multiplicative backoff base (seconds)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_page(
    url: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    headers: Optional[dict] = None,
) -> str:
    """Fetch a URL and return the response body as text.

    Parameters
    ----------
    url : str
        Target page URL.
    timeout : int
        HTTP request timeout in seconds.
    retries : int
        Number of retry attempts on transient failures.
    headers : dict or None
        Custom request headers; falls back to a browser-like default.

    Returns
    -------
    str
        Raw HTML content.

    Raises
    ------
    requests.RequestException
        If all retry attempts are exhausted.
    """
    effective_headers = HEADERS if headers is None else headers

    last_exc: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            logger.debug("Fetching %s (attempt %d/%d)", url, attempt, retries)
            resp = requests.get(
                url, headers=effective_headers, timeout=timeout
            )
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            last_exc = exc
            logger.warning(
                "Request failed (attempt %d/%d): %s", attempt, retries, exc
            )
            if attempt < retries:
                delay = RETRY_BACKOFF ** attempt
                time.sleep(delay)

    raise requests.RequestException(
        f"Failed to fetch {url} after {retries} attempts"
    ) from last_exc


def parse_price(
    html: str,
    css_selector: str,
    *,
    regex: Optional[str] = None,
    index: int = 0,
) -> Optional[float]:
    """Extract a price from HTML using a CSS selector.

    Parameters
    ----------
    html : str
        Raw HTML to parse.
    css_selector : str
        CSS selector that targets the element(s) containing the price.
    regex : str or None
        Optional regex to extract the numeric part from the element text.
        When omitted, the first float-like number in the text is used.
    index : int
        Which matching element to use (0-based).

    Returns
    -------
    float or None
        The extracted price, or ``None`` if nothing matched.
    """
    soup = BeautifulSoup(html, "html.parser")
    elements = soup.select(css_selector)

    if not elements or index >= len(elements):
        logger.warning(
            "Selector %r returned %d element(s); index %d is out of range",
            css_selector, len(elements), index,
        )
        return None

    text = elements[index].get_text(strip=True)
    logger.debug("Raw element text: %r", text)

    if regex:
        match = re.search(regex, text)
        if match:
            raw = match.group(1) if match.lastindex else match.group()
        else:
            logger.warning("Regex %r did not match text %r", regex, text)
            return None
    else:
        # Heuristic: grab the first token that looks like a decimal number
        match = re.search(r"\d+(?:[.,]\d{1,2})?", text)
        raw = match.group() if match else None

    if raw is None:
        return None

    # Normalise: "1.299,99" → 1299.99 ; "$19.99" → 19.99
    return _normalise_price(raw)


def get_current_price(
    url: str,
    css_selector: str,
    *,
    regex: Optional[str] = None,
    **kwargs,
) -> Optional[float]:
    """Convenience: fetch a page and extract the price in one call.

    All extra keyword arguments are forwarded to :func:`fetch_page`.
    """
    html = fetch_page(url, **kwargs)
    return parse_price(html, css_selector, regex=regex)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalise_price(raw: str) -> float:
    """Convert a locale-agnostic price string into a float.

    Examples
    --------
    >>> _normalise_price("1.299,99")
    1299.99
    >>> _normalise_price("$19.99")
    19.99
    >>> _normalise_price("1299")
    1299.0
    """
    # Strip currency symbols / whitespace before format detection
    cleaned = re.sub(r"[^\d.,\-]", "", raw).strip()

    # Detect European format: dot = thousand-sep, comma = decimal
    # Heuristic: if comma appears *after* the last dot, it's European
    last_dot = cleaned.rfind(".")
    last_comma = cleaned.rfind(",")
    if last_comma > last_dot and last_comma >= 0:
        # European: 1.299,99 → remove dots, replace comma with dot
        cleaned = cleaned.replace(".", "").replace(",", ".")
    else:
        # US/UK: 1,299.99 → remove commas, keep dot
        cleaned = cleaned.replace(",", "")

    # Strip any remaining non-numeric chars except dot & minus
    cleaned = re.sub(r"[^\d.\-]", "", cleaned)

    try:
        return float(cleaned)
    except ValueError:
        logger.warning("Could not convert %r to float after cleaning", raw)
        return None
