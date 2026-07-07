"""
Price scraper module — fetches web pages and extracts price information.

Supports CSS-selector based extraction with configurable headers,
retry logic, and graceful error handling.

Error handling covers:
  - Network timeout (requests.exceptions.Timeout)
  - Connection errors (requests.exceptions.ConnectionError)
  - HTTP status errors (requests.exceptions.HTTPError)
  - Page structure changes (selector mismatch → diagnostic dump)
"""

import re
import time
import logging
import textwrap
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

        # ---- 网络超时 ----
        except requests.exceptions.Timeout as exc:
            last_exc = exc
            logger.warning(
                "⏱ 网络超时 (>%ds) — 第 %d/%d 次尝试: %s",
                timeout, attempt, retries, exc,
            )
            if attempt == retries:
                logger.error(
                    "已达最大重试次数 (%d)。可能原因:\n"
                    "  1) 服务器响应过慢\n"
                    "  2) 网络不稳定\n"
                    "  3) DNS 解析缓慢\n"
                    "  建议: 增大 config.py 中的超时时间或 CHECK_INTERVAL",
                    retries,
                )
            elif attempt < retries:
                delay = RETRY_BACKOFF ** attempt
                logger.info("  → %ds 后重试...", delay)
                time.sleep(delay)

        # ---- 连接错误（DNS失败 / 拒绝连接 / 断网） ----
        except requests.exceptions.ConnectionError as exc:
            last_exc = exc
            logger.warning(
                "🔌 连接失败 — 第 %d/%d 次尝试: %s",
                attempt, retries, exc,
            )
            if attempt == retries:
                logger.error(
                    "已达最大重试次数 (%d)。可能原因:\n"
                    "  1) 网络断开\n"
                    "  2) DNS 无法解析域名\n"
                    "  3) 目标服务器拒绝连接（IP 被封？）\n"
                    "  4) 代理设置错误\n"
                    "  建议: 检查网络连接，尝试用浏览器访问 %s",
                    retries, url,
                )
            elif attempt < retries:
                delay = RETRY_BACKOFF ** attempt
                logger.info("  → %ds 后重试...", delay)
                time.sleep(delay)

        # ---- HTTP 状态错误（4xx / 5xx） ----
        except requests.exceptions.HTTPError as exc:
            last_exc = exc
            status = exc.response.status_code if exc.response is not None else "?"
            if 400 <= (exc.response.status_code if exc.response else 0) < 500:
                # 4xx: 客户端错误，不重试
                logger.error(
                    "🚫 HTTP %s — 客户端错误，不重试。\n"
                    "  可能原因: 1) 页面不存在 (404)  2) 被反爬拦截 (403)  3) URL 错误",
                    status,
                )
                raise  # 4xx 直接抛出，不重试
            else:
                # 5xx: 服务端错误，可重试
                logger.warning(
                    "⚠ HTTP %s — 服务端错误，第 %d/%d 次尝试",
                    status, attempt, retries,
                )
                if attempt < retries:
                    delay = RETRY_BACKOFF ** attempt
                    logger.info("  → %ds 后重试...", delay)
                    time.sleep(delay)

        # ---- 其他 requests 异常 ----
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            logger.warning(
                "网络请求异常 (%s) — 第 %d/%d 次尝试: %s",
                type(exc).__name__, attempt, retries, exc,
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
    # ---- 解析 HTML ----
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as exc:
        logger.error("HTML 解析失败: %s: %s", type(exc).__name__, exc)
        return None

    # ---- 查找目标元素 ----
    try:
        elements = soup.select(css_selector)
    except Exception as exc:
        logger.error(
            "CSS 选择器语法错误 '%s': %s: %s",
            css_selector, type(exc).__name__, exc,
        )
        logger.info("请检查 config.py 中的 CSS_SELECTOR 是否合法")
        return None

    if not elements or index >= len(elements):
        logger.warning(
            "⚠ 页面结构变更！选择器 '%s' 匹配到 %d 个元素，索引 %d 超出范围",
            css_selector, len(elements), index,
        )
        logger.info(
            "可能原因:\n"
            "  1) 目标网站改版，HTML 结构已变更\n"
            "  2) 反爬虫机制返回了不同的页面\n"
            "  3) CSS_SELECTOR 需要更新\n"
            "  建议: 打开 %s → F12 开发者工具 → 找到价格元素 → 更新 CSS_SELECTOR",
            "目标页面",
        )
        # 打印页面中可能包含价格的元素，帮助诊断
        _dump_price_candidates(soup)
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
        logger.warning(
            "⚠ 价格格式变更！元素文本 '%s' 中未找到数字", text,
        )
        logger.info(
            "可能原因:\n"
            "  1) 价格展示格式已改变\n"
            "  2) 价格通过 JS 动态加载（页面抓取不到）\n"
            "  3) 需要配置 PRICE_REGEX 来匹配特殊格式"
        )
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


def _dump_price_candidates(soup: BeautifulSoup, top_n: int = 10) -> None:
    """Scan the page for elements likely to contain price information.

    Called when the configured CSS selector fails, to help the user
    identify the new selector needed after a page structure change.
    """
    # 搜索常见价格相关的 class / id / 属性
    candidates = set()
    for tag in soup.find_all(True):  # True = all tags
        if not hasattr(tag, "name") or tag.name is None:
            continue

        text = tag.get_text(strip=True)
        if not text:
            continue

        # 检查文本是否包含数字（可能是价格）
        if not re.search(r"\d", text):
            continue

        # 构建 CSS 提示
        tag_id = f"#{tag.get('id')}" if tag.get("id") else ""
        classes = ".".join(tag.get("class", [])) if tag.get("class") else ""
        css_hint = f"{tag.name}{tag_id}{'.' + classes if classes else ''}"

        # 检查 class/id 是否暗示价格
        hint_lower = (tag.get("id", "") + " " + " ".join(tag.get("class", []))).lower()
        is_price_like = any(
            kw in hint_lower
            for kw in ["price", "p-price", "product-price", "amount", "cost", "value"]
        )

        if is_price_like and css_hint not in candidates:
            text_short = textwrap.shorten(text, width=50, placeholder="...")
            # 尝试提取数字部分
            num_match = re.search(r"\d[\d,.]*", text.replace("¥", "").replace("￥", ""))
            num_preview = f" → {num_match.group()}" if num_match else ""
            candidates.add((css_hint, text_short, num_preview))

    if candidates:
        logger.info("--- 页面中可能包含价格的元素 (建议更新 CSS_SELECTOR) ---")
        for css_hint, text, num in sorted(candidates)[:top_n]:
            logger.info("  %s: '%s'%s", css_hint, text, num)
    else:
        logger.warning(
            "未在页面中找到疑似价格元素。\n"
            "  可能原因:\n"
            "  1) 页面内容为 JS 动态渲染（requests 无法执行 JS）\n"
            "  2) 页面被反爬机制拦截\n"
            "  3) 价格通过 API 异步加载\n"
            "  建议: 在浏览器中打开页面 → 检查价格元素是否在初始 HTML 中"
        )


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
