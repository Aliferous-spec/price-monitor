# -*- coding: utf-8 -*-
"""
visualization.py — 价格走势可视化模块

使用 matplotlib 生成商品价格历史走势图。
内置 --demo 模式可直接生成演示图表（无需真实爬虫数据），
也支持从 JSON-lines 历史文件加载真实数据绘图。

用法:
    python visualization.py --demo              # 生成演示图表 → price_chart.png
    python visualization.py --file price_history.jsonl  # 从历史数据生成
    python visualization.py --demo --output my_chart.png  # 指定输出路径
"""

from __future__ import annotations

import json
import logging
import os
import sys
import argparse
from datetime import datetime, timedelta
from typing import List, Optional

import matplotlib
matplotlib.use("Agg")  # 非交互后端，无需 GUI 即可出图
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 中文字体配置 — 按优先级尝试
# ---------------------------------------------------------------------------
_FONT_CANDIDATES = [
    "Microsoft YaHei",   # Windows
    "SimHei",            # Windows 备选
    "PingFang SC",       # macOS
    "Heiti SC",          # macOS 备选
    "Noto Sans CJK SC",  # Linux
    "WenQuanYi Micro Hei",
    "DejaVu Sans",       # 最后的回退（不支持中文但不报错）
]
for _font in _FONT_CANDIDATES:
    try:
        plt.rcParams["font.sans-serif"] = [_font] + plt.rcParams["font.sans-serif"]
        # 测试是否能渲染中文
        fig_test, ax_test = plt.subplots(figsize=(1, 1))
        ax_test.set_title("测试")
        plt.close(fig_test)
        _CHINESE_FONT = _font
        break
    except Exception:
        continue
else:
    _CHINESE_FONT = "DejaVu Sans"

plt.rcParams["axes.unicode_minus"] = False  # 正确显示负号

# ---------------------------------------------------------------------------
# 颜色常量
# ---------------------------------------------------------------------------
COLOR_PRIMARY = "#2B6CB0"     # 价格主线
COLOR_FILL = "#BEE3F8"        # 面积填充
COLOR_MA = "#DD6B20"         # 移动平均线
COLOR_DROP = "#E53E3E"       # 降价标记
COLOR_LOWEST = "#38A169"     # 最低价标记
COLOR_GRID = "#E2E8F0"       # 网格线
COLOR_BG = "#FFFFFF"         # 背景

# ---------------------------------------------------------------------------
# Demo 数据生成
# ---------------------------------------------------------------------------

def generate_demo_data(output_path: str = "demo_history.jsonl") -> str:
    """生成 30 天真实感价格演示数据，写入 JSON-lines 文件。

    模拟场景：一款蓝牙耳机在电商平台 30 天内的价格波动——
    包含日常浮动、限时秒杀、大促降价、价格回调，贴近真实电商价格曲线。

    Returns:
        output_path: 生成的数据文件路径
    """
    # 产品信息（用于模拟数据的注释）
    product_url = "https://item.jd.com/demo-100066207842.html"

    # 价格曲线设计（30 天，模拟真实电商行为）
    # 日常价 ~¥399，促销时降至 ¥299，大促探底 ¥269
    base_price = 399.0

    # 每日价格生成规则（在基准价基础上叠加多种波动）
    daily_pattern = [
        # day 1-6: 日常波动
        399, 405, 398, 402, 395, 400,
        # day 7-8: 周末小幅促销
        389, 379,
        # day 9-13: 回弹 + 日常
        399, 404, 398, 409, 396,
        # day 14-16: 限时秒杀
        369, 349, 339,
        # day 17: 秒杀结束回弹
        399,
        # day 18-20: 618 大促
        319, 299, 269,
        # day 21-23: 大促后回弹
        349, 379, 399,
        # day 24-28: 日常波动
        404, 399, 389, 395, 399,
        # day 29-30: 近期
        389, 379,
    ]

    # 叠加微量随机噪声（±3 元），让曲线更自然
    rng = np.random.RandomState(42)  # 固定种子，保证每次生成一致
    noise = [round(rng.uniform(-3, 3), 2) for _ in range(len(daily_pattern))]
    prices = [round(p + n, 2) for p, n in zip(daily_pattern, noise)]

    # 生成时间戳（从 30 天前到今天，每天一条记录）
    today = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
    start_date = today - timedelta(days=len(prices) - 1)

    records = []
    for i, price in enumerate(prices):
        ts = (start_date + timedelta(days=i)).isoformat()
        records.append({
            "timestamp": ts,
            "url": product_url,
            "price": price,
            "currency": "CNY",
        })

    # 写入 JSON-lines 文件
    with open(output_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    logger.info("Demo data: %d records → %s", len(records), output_path)
    return output_path


# ---------------------------------------------------------------------------
# 数据加载
# ---------------------------------------------------------------------------

def load_price_data(filepath: str) -> List[dict]:
    """从 JSON-lines 文件加载价格记录。

    兼容 storage.py 的 PriceRecord 格式：
    {"timestamp": "2026-07-01T12:00:00", "url": "...", "price": 399.0, "currency": "CNY"}

    Returns:
        按时间升序排列的记录列表（已过滤无效行）
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"数据文件不存在: {filepath}")

    records = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                # 确保必要字段存在
                if "price" not in obj or "timestamp" not in obj:
                    logger.warning("Skipping record missing price/timestamp: %s", line[:80])
                    continue
                records.append(obj)
            except json.JSONDecodeError:
                logger.warning("Skipping invalid JSON line: %s", line[:80])

    # 按时间排序
    records.sort(key=lambda r: r["timestamp"])
    return records


# ---------------------------------------------------------------------------
# 核心绘图
# ---------------------------------------------------------------------------

def plot_price_history(
    records: List[dict],
    output_path: str = "price_chart.png",
    *,
    title: Optional[str] = None,
    show_moving_average: bool = True,
    window: int = 7,
) -> str:
    """根据价格历史记录生成走势图。

    Args:
        records: 价格记录列表，每条含 timestamp / price
        output_path: 输出 PNG 文件路径
        title: 图表标题，默认自动生成
        show_moving_average: 是否显示移动平均线
        window: 移动平均窗口大小（天）

    Returns:
        output_path: 生成的图片路径
    """
    if len(records) < 2:
        raise ValueError(f"至少需要 2 条记录才能绘图，当前只有 {len(records)} 条")

    # ---- 解析数据 ----
    timestamps = [datetime.fromisoformat(r["timestamp"]) for r in records]
    prices = [r["price"] for r in records]

    # ---- 创建画布 ----
    fig, ax = plt.subplots(figsize=(13, 6))
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)

    # ---- 面积填充（先画，在折线下方） ----
    ax.fill_between(timestamps, prices, min(prices) * 0.98,
                    alpha=0.12, color=COLOR_PRIMARY, linewidth=0)

    # ---- 价格主线 ----
    ax.plot(timestamps, prices,
            color=COLOR_PRIMARY, linewidth=2.2, marker="o",
            markersize=5, markerfacecolor="white",
            markeredgewidth=1.5, markeredgecolor=COLOR_PRIMARY,
            zorder=5, label="日价格")

    # ---- 移动平均线 ----
    if show_moving_average and len(prices) >= window:
        ma = _moving_average(prices, window)
        # MA 的 x 轴对齐：取最后 len(ma) 个时间点
        ax.plot(timestamps[-len(ma):], ma,
                color=COLOR_MA, linewidth=1.8, linestyle="--",
                dashes=(6, 3), alpha=0.85, zorder=4,
                label=f"{window}日均价")

    # ---- 标注最低价 ----
    min_idx = int(np.argmin(prices))
    min_price = prices[min_idx]
    ax.scatter([timestamps[min_idx]], [min_price],
               color=COLOR_LOWEST, s=80, zorder=10, edgecolors="white", linewidth=1.5)
    ax.annotate(
        f"最低 ¥{min_price:.0f}",
        xy=(timestamps[min_idx], min_price),
        xytext=(0, -22), textcoords="offset points",
        ha="center", va="top", fontsize=9, color=COLOR_LOWEST, fontweight="bold",
        arrowprops=dict(arrowstyle="->", color=COLOR_LOWEST, lw=1.5,
                        connectionstyle="arc3,rad=0.2"),
    )

    # ---- 标注最新价 ----
    latest_price = prices[-1]
    ax.scatter([timestamps[-1]], [latest_price],
               color=COLOR_PRIMARY, s=80, zorder=10, edgecolors="white", linewidth=1.5)
    ax.annotate(
        f"当前 ¥{latest_price:.0f}",
        xy=(timestamps[-1], latest_price),
        xytext=(12, 0), textcoords="offset points",
        ha="left", va="center", fontsize=10, color=COLOR_PRIMARY, fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor=COLOR_PRIMARY,
                  alpha=0.9),
    )

    # ---- 标注显著降价点 (>5%) ----
    for i in range(1, len(prices)):
        drop_pct = (prices[i - 1] - prices[i]) / prices[i - 1] * 100
        if drop_pct > 5:
            ax.annotate(
                f"↓{drop_pct:.0f}%",
                xy=(timestamps[i], prices[i]),
                xytext=(0, 14), textcoords="offset points",
                ha="center", fontsize=7.5, color=COLOR_DROP, fontweight="bold",
            )

    # ---- 参考线：起始价 ----
    start_price = prices[0]
    ax.axhline(y=start_price, color="#A0AEC0", linewidth=0.8,
               linestyle=":", alpha=0.6, zorder=1)
    ax.annotate(
        f"起始 ¥{start_price:.0f}",
        xy=(timestamps[0], start_price),
        xytext=(8, 4), textcoords="offset points",
        ha="left", fontsize=8, color="#A0AEC0",
    )

    # ---- 坐标轴格式 ----
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("¥%.0f"))
    fig.autofmt_xdate(rotation=0, ha="center")

    # 留出上下空间给标注
    y_min, y_max = min(prices), max(prices)
    y_padding = (y_max - y_min) * 0.25
    ax.set_ylim(y_min - y_padding, y_max + y_padding)

    # ---- 网格 & 边框 ----
    ax.grid(True, axis="y", alpha=0.35, color=COLOR_GRID, linewidth=0.6)
    ax.grid(True, axis="x", alpha=0.15, color=COLOR_GRID, linewidth=0.6)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CBD5E0")
    ax.spines["bottom"].set_color("#CBD5E0")

    # ---- 标题 & 标签 ----
    if title is None:
        # 尝试从 URL 提取域名
        url = records[0].get("url", "")
        source_hint = ""
        if "jd.com" in url:
            source_hint = " · 京东"
        elif "taobao.com" in url:
            source_hint = " · 淘宝"
        title = f"商品价格走势{source_hint}"

    ax.set_title(title, fontsize=16, fontweight="bold", pad=16,
                 color="#1A202C")
    ax.set_ylabel("价格", fontsize=11, color="#4A5568")
    ax.legend(loc="upper right", frameon=True, framealpha=0.85,
              edgecolor=COLOR_GRID, fontsize=9)

    # ---- 底部统计信息 ----
    price_range = max(prices) - min(prices)
    stats_text = (
        f"30天最高 ¥{max(prices):.0f}  |  "
        f"最低 ¥{min_price:.0f}  |  "
        f"波动 ¥{price_range:.0f}  |  "
        f"当前 ¥{latest_price:.0f}"
    )
    fig.text(0.5, 0.01, stats_text, ha="center", fontsize=8.5,
             color="#718096", transform=fig.transFigure)

    # ---- 保存 ----
    fig.tight_layout(rect=[0, 0.04, 1, 0.98])
    fig.savefig(output_path, dpi=150, facecolor=COLOR_BG, edgecolor="none",
                bbox_inches="tight")
    plt.close(fig)

    logger.info("图表已保存 → %s (%d 条记录)", output_path, len(records))
    return output_path


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _moving_average(values: List[float], window: int) -> List[float]:
    """计算简单移动平均（SMA），结果长度 = len(values) - window + 1。"""
    if len(values) < window:
        return values[:]
    arr = np.array(values)
    return np.convolve(arr, np.ones(window) / window, mode="valid").tolist()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        description="价格走势可视化 — 用 matplotlib 生成价格历史走势图",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--demo", "-d",
        action="store_true",
        help="生成 30 天模拟数据并绘制演示图表",
    )
    group.add_argument(
        "--file", "-f",
        type=str,
        metavar="PATH",
        help="从 JSON-lines 历史文件加载数据并绘图",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="price_chart.png",
        help="输出图片路径 (默认: price_chart.png)",
    )
    parser.add_argument(
        "--title", "-t",
        type=str,
        default=None,
        help="图表标题",
    )
    parser.add_argument(
        "--no-ma",
        action="store_true",
        help="不显示移动平均线",
    )

    args = parser.parse_args()

    try:
        if args.file:
            # 从用户指定的历史文件加载
            records = load_price_data(args.file)
            logger.info("从 %s 加载了 %d 条价格记录", args.file, len(records))
        elif args.demo:
            # 生成 demo 数据
            demo_file = generate_demo_data("demo_history.jsonl")
            records = load_price_data(demo_file)
        else:
            # 默认：尝试加载 price_history.jsonl，找不到则自动进入 demo 模式
            if os.path.isfile("price_history.jsonl"):
                records = load_price_data("price_history.jsonl")
                logger.info("从 price_history.jsonl 加载了 %d 条记录", len(records))
            else:
                logger.info("未找到 price_history.jsonl，自动进入 demo 模式")
                demo_file = generate_demo_data("demo_history.jsonl")
                records = load_price_data(demo_file)

        plot_price_history(
            records,
            output_path=args.output,
            title=args.title,
            show_moving_average=not args.no_ma,
        )

        print(f"\n[OK] 图表已生成: {os.path.abspath(args.output)}")
        print(f"     共 {len(records)} 条价格记录")
        print(f"     价格区间: {min(r['price'] for r in records):.2f} ~ "
              f"{max(r['price'] for r in records):.2f}")

    except FileNotFoundError as e:
        logger.error("文件未找到: %s", e)
        sys.exit(1)
    except ValueError as e:
        logger.error("数据不足: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("生成图表时出错: %s: %s", type(e).__name__, e)
        sys.exit(1)


if __name__ == "__main__":
    main()
