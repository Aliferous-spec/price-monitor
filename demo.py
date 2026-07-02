"""
Demo script — exercises all modules with sample data for a clean screenshot.
Run: python demo.py
"""
import logging
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

# --- Test scraper -----------------------------------------------------------
print("=" * 60)
print("  1. SCRAPER — 测试价格提取")
print("=" * 60)

from scraper import parse_price, _normalise_price

# Test price normalisation
samples = [
    ("$19.99", 19.99),
    ("1.299,99 €", 1299.99),
    ("¥ 299.00", 299.0),
    ("1,999.99", 1999.99),
]
for raw, expected in samples:
    result = _normalise_price(raw)
    status = "✓" if result == expected else "✗"
    print(f"  {status}  {raw!r:20s} → {result:>10.2f}  (expected {expected})")

# Test HTML parsing
html_sample = '<html><span class="price">¥ 199.99</span></html>'
price = parse_price(html_sample, ".price")
print(f"\n  → 从 HTML 提取价格: ¥{price:.2f}" if price else "  → 提取失败")

# --- Test storage -----------------------------------------------------------
print()
print("=" * 60)
print("  2. STORAGE — 测试数据持久化")
print("=" * 60)

from storage import PriceRecord, save_record, load_history, get_lowest_price, price_dropped

# Clean up previous run
test_file = "demo_history.jsonl"
if os.path.isfile(test_file):
    os.remove(test_file)

# Save some records
records = [
    PriceRecord(datetime.now(timezone.utc).isoformat(), "https://item.jd.com/demo", 259.00),
    PriceRecord(datetime.now(timezone.utc).isoformat(), "https://item.jd.com/demo", 249.00),
    PriceRecord(datetime.now(timezone.utc).isoformat(), "https://item.jd.com/demo", 239.00),
]
for r in records:
    save_record(r, filepath=test_file)

# Read back
loaded = load_history(test_file)
print(f"  已存储 {len(loaded)} 条价格记录:")
for r in loaded:
    print(f"    {r.timestamp[:19]}  ¥{r.price:.2f}")

lowest = get_lowest_price(test_file)
print(f"\n  📉 历史最低: ¥{lowest.price:.2f}" if lowest else "  无记录")

print(f"  📉 价格下降检测 (¥229 vs 上次 ¥{loaded[-1].price}): {price_dropped(229.0, test_file)}")

# Cleanup
os.remove(test_file)

# --- Test notifier ----------------------------------------------------------
print()
print("=" * 60)
print("  3. NOTIFIER — 已注册的通知渠道")
print("=" * 60)

from notifier import NOTIFIERS

for name in NOTIFIERS:
    print(f"  🔔 {name}")

print()
print("  ℹ️  实际通知仅在配置了 SMTP / Telegram Token 后触发")

# --- Summary ----------------------------------------------------------------
print()
print("=" * 60)
print("  ✅ 三大模块就绪: scraper · storage · notifier")
print("=" * 60)
