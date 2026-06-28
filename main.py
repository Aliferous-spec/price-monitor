# -*- coding: utf-8 -*-
"""
商品价格监控工具 - 主程序
自动监控商品价格变化，降价时发送邮件通知。

用法:
    python main.py              # 运行一次检查
    python main.py --schedule   # 启动定时监控
    python main.py --test-email # 测试邮件配置
"""

import sys
import time
import argparse
from datetime import datetime

import config
from price_scraper import get_product_price
from price_store import save_price, get_latest_price, get_lowest_price
from email_notifier import send_price_alert, send_test_email
from chart_generator import generate_all_charts


def check_prices():
    """
    检查所有商品价格并处理降价通知
    """
    print(f"\n{'='*50}")
    print(f"🔍 价格检查 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    for product in config.PRODUCTS:
        print(f"\n📦 正在检查: {product['name']}")

        # 抓取当前价格
        result = get_product_price(product)

        if not result["success"]:
            print(f"  ❌ 获取失败: {result.get('error', '未知错误')}")
            continue

        current_price = result["price"]
        print(f"  💰 当前价格: ¥{current_price}")

        # 获取上次价格
        previous_price = get_latest_price(product["name"], config.CSV_FILE)
        lowest_price = get_lowest_price(product["name"], config.CSV_FILE)

        # 保存当前价格
        save_price(product["name"], current_price, config.CSV_FILE)

        # 判断是否需要发送降价通知
        should_notify = False

        if previous_price is not None and current_price < previous_price:
            print(f"  📉 降价了！上次: ¥{previous_price} → 当前: ¥{current_price}")
            should_notify = True

        if product.get("target_price") and current_price <= product["target_price"]:
            print(f"  🎯 价格已达到目标价 ¥{product['target_price']}")
            should_notify = True

        if lowest_price is not None and current_price < lowest_price:
            print(f"  🏆 创历史新低！之前最低: ¥{lowest_price}")

        if should_notify:
            send_price_alert(
                smtp_server=config.EMAIL_CONFIG["smtp_server"],
                smtp_port=config.EMAIL_CONFIG["smtp_port"],
                sender_email=config.EMAIL_CONFIG["sender_email"],
                sender_password=config.EMAIL_CONFIG["sender_password"],
                receiver_email=config.EMAIL_CONFIG["receiver_email"],
                product_name=product["name"],
                current_price=current_price,
                previous_price=previous_price or current_price,
                product_url=product["url"],
                lowest_price=lowest_price,
            )

    # 生成价格走势图
    print(f"\n📊 生成价格走势图...")
    generate_all_charts(config.PRODUCTS, config.CSV_FILE)

    print(f"\n✅ 检查完成\n")


def run_schedule():
    """
    定时运行价格检查
    """
    try:
        import schedule
    except ImportError:
        print("请先安装 schedule: pip install schedule")
        return

    interval = config.CHECK_INTERVAL_MINUTES
    print(f"\n⏰ 定时监控已启动，每 {interval} 分钟检查一次")
    print("按 Ctrl+C 停止\n")

    # 立即执行一次
    check_prices()

    # 定时执行
    schedule.every(interval).minutes.do(check_prices)

    try:
        while True:
            schedule.run_pending()
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n👋 监控已停止")


def main():
    parser = argparse.ArgumentParser(
        description="商品价格监控工具 - 自动抓取价格，降价邮件通知"
    )
    parser.add_argument(
        "--schedule", "-s",
        action="store_true",
        help="启动定时监控模式",
    )
    parser.add_argument(
        "--test-email",
        action="store_true",
        help="测试邮件配置是否正常",
    )
    parser.add_argument(
        "--once", "-o",
        action="store_true",
        help="运行一次检查（默认行为）",
    )

    args = parser.parse_args()

    if args.test_email:
        print("📧 测试邮件配置...")
        send_test_email(config.EMAIL_CONFIG)
    elif args.schedule:
        run_schedule()
    else:
        # 默认运行一次
        check_prices()


if __name__ == "__main__":
    main()
