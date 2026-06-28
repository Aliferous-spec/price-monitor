# -*- coding: utf-8 -*-
"""
价格数据存储模块
使用CSV文件存储历史价格数据
"""

import csv
import os
from datetime import datetime
from typing import Optional


def save_price(product_name: str, price: float, csv_file: str = "price_history.csv"):
    """
    保存一条价格记录到CSV

    格式: 商品名称, 日期时间, 价格
    """
    file_exists = os.path.isfile(csv_file)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(csv_file, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        # 新文件写入表头
        if not file_exists or os.path.getsize(csv_file) == 0:
            writer.writerow(["商品名称", "记录时间", "价格(元)"])
        writer.writerow([product_name, now, price])


def load_history(csv_file: str = "price_history.csv") -> list[dict]:
    """
    从CSV加载所有历史记录

    Returns:
        [{"商品名称": ..., "记录时间": ..., "价格(元)": ...}, ...]
    """
    if not os.path.isfile(csv_file):
        return []

    records = []
    with open(csv_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["价格(元)"] = float(row["价格(元)"])
            records.append(row)
    return records


def get_product_history(product_name: str, csv_file: str = "price_history.csv") -> list[dict]:
    """
    获取某个商品的历史价格

    Returns:
        该商品所有记录，按时间升序
    """
    all_records = load_history(csv_file)
    product_records = [
        r for r in all_records
        if r["商品名称"] == product_name
    ]
    product_records.sort(key=lambda r: r["记录时间"])
    return product_records


def get_latest_price(product_name: str, csv_file: str = "price_history.csv") -> Optional[float]:
    """
    获取某商品的最近一次价格
    """
    history = get_product_history(product_name, csv_file)
    if history:
        return history[-1]["价格(元)"]
    return None


def get_lowest_price(product_name: str, csv_file: str = "price_history.csv") -> Optional[float]:
    """
    获取某商品的历史最低价
    """
    history = get_product_history(product_name, csv_file)
    if history:
        return min(r["价格(元)"] for r in history)
    return None
