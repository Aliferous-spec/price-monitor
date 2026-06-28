# -*- coding: utf-8 -*-
"""
价格抓取模块
使用 requests + BeautifulSoup 从网页抓取商品价格
"""

import re
import requests
from bs4 import BeautifulSoup

# 请求头，模拟浏览器访问
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}


def fetch_page(url: str, timeout: int = 15) -> str:
    """
    获取网页HTML内容

    Args:
        url: 商品页面URL
        timeout: 请求超时时间

    Returns:
        HTML字符串

    Raises:
        requests.RequestException: 网络请求失败
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    return response.text


def extract_price(html: str, css_selector: str) -> float:
    """
    从HTML中提取价格

    Args:
        html: 页面HTML
        css_selector: 价格元素的CSS选择器

    Returns:
        价格（浮点数），提取失败返回 -1
    """
    soup = BeautifulSoup(html, "html.parser")
    element = soup.select_one(css_selector)

    if not element:
        # 备用方案：尝试用正则在整个页面中匹配价格
        return _extract_price_by_regex(html)

    text = element.get_text(strip=True)
    return _parse_price_text(text)


def _parse_price_text(text: str) -> float:
    """
    从文本中解析价格数字

    支持格式: ¥19.99, 19.99元, $29.99, 19.99
    """
    # 移除常见符号，提取数字和小数点
    cleaned = re.sub(r"[^\d.]", "", text)
    try:
        price = float(cleaned)
        return round(price, 2)
    except ValueError:
        return -1.0


def _extract_price_by_regex(html: str) -> float:
    """
    正则备用提取价格

    匹配中文价格常见的模式（不完美）
    """
    # 价格常见模式: ¥符号后跟数字
    patterns = [
        r"¥\s*(\d+\.?\d*)",
        r"￥\s*(\d+\.?\d*)",
        r"价格[：:]\s*(\d+\.?\d*)",
        r"price[：:\s]+(\d+\.?\d*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            try:
                return round(float(match.group(1)), 2)
            except ValueError:
                continue
    return -1.0


def get_product_price(product: dict) -> dict:
    """
    获取单个商品的价格

    Args:
        product: 商品信息字典，包含 name, url, css_selector

    Returns:
        {"name": ..., "url": ..., "price": ..., "success": ...}
    """
    result = {
        "name": product["name"],
        "url": product["url"],
        "price": -1.0,
        "success": False,
    }

    try:
        html = fetch_page(product["url"])
        price = extract_price(html, product["css_selector"])
        if price > 0:
            result["price"] = price
            result["success"] = True
    except requests.RequestException as e:
        result["error"] = f"网络请求失败: {e}"
    except Exception as e:
        result["error"] = f"解析失败: {e}"

    return result
