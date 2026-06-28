# -*- coding: utf-8 -*-
"""
价格走势图表生成模块
使用 matplotlib 生成价格历史趋势图
"""

import matplotlib
matplotlib.use("Agg")  # 非交互后端，无需GUI
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime


def generate_price_chart(
    product_name: str,
    records: list[dict],
    output_path: str = "price_chart.png",
):
    """
    生成单个商品的价格走势图

    Args:
        product_name: 商品名称
        records: 历史价格记录，每项包含 "记录时间" 和 "价格(元)"
        output_path: 输出图片路径
    """
    if not records:
        print(f"  ⚠️ {product_name} 无历史数据，跳过图表生成")
        return

    # 解析数据
    times = [datetime.strptime(r["记录时间"], "%Y-%m-%d %H:%M:%S") for r in records]
    prices = [r["价格(元)"] for r in records]

    # 设置中文字体
    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(10, 5))

    # 绘制价格曲线
    ax.plot(times, prices, marker="o", linewidth=2, markersize=4, color="#2196F3")
    ax.fill_between(times, min(prices), prices, alpha=0.15, color="#2196F3")

    # 标注最高和最低点
    min_idx = prices.index(min(prices))
    max_idx = prices.index(max(prices))
    ax.annotate(f"最低 ¥{prices[min_idx]}",
                xy=(times[min_idx], prices[min_idx]),
                xytext=(0, -20), textcoords="offset points",
                ha="center", fontsize=9, color="green",
                arrowprops=dict(arrowstyle="->", color="green"))
    ax.annotate(f"最高 ¥{prices[max_idx]}",
                xy=(times[max_idx], prices[max_idx]),
                xytext=(0, 12), textcoords="offset points",
                ha="center", fontsize=9, color="red",
                arrowprops=dict(arrowstyle="->", color="red"))

    # 格式化
    ax.set_title(f"📊 {product_name} 价格走势", fontsize=14, fontweight="bold")
    ax.set_xlabel("日期")
    ax.set_ylabel("价格 (元)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d\n%H:%M"))
    ax.grid(True, alpha=0.3)
    ax.legend(["价格"], loc="upper right")

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

    print(f"  📈 价格走势图已保存 → {output_path}")


def generate_all_charts(products: list[dict], csv_file: str = "price_history.csv"):
    """
    为所有商品生成价格走势图
    """
    from price_store import get_product_history

    for product in products:
        history = get_product_history(product["name"], csv_file)
        if history:
            filename = f"chart_{product['name'][:10]}.png"
            generate_price_chart(product["name"], history, filename)
