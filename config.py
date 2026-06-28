# -*- coding: utf-8 -*-
"""
价格监控器配置
修改以下配置以适应你的需求
"""

# ========== 监控商品列表 ==========
# 每个商品包含: name(名称), url(商品链接), css_selector(价格所在的CSS选择器)
PRODUCTS = [
    {
        "name": "示例商品 - 京东某商品",
        "url": "https://item.jd.com/100012345678.html",
        # CSS选择器：京东价格通常用 .p-price 或 span.price
        "css_selector": "span.price",
        # 期望降价到多少元以下时通知（可选）
        "target_price": None,
    },
    # 继续添加更多商品，例如：
    # {
    #     "name": "淘宝某商品",
    #     "url": "https://item.taobao.com/item.htm?id=123456",
    #     "css_selector": "span.tb-rmb-num",
    #     "target_price": 50.0,
    # },
]

# ========== 检查间隔 ==========
# 检查间隔（分钟）
CHECK_INTERVAL_MINUTES = 60

# ========== 邮件通知配置 ==========
EMAIL_CONFIG = {
    # 发件人邮箱（QQ邮箱为例）
    "smtp_server": "smtp.qq.com",
    "smtp_port": 587,
    "sender_email": "your_email@qq.com",
    # QQ邮箱需使用授权码，不是登录密码！
    # 获取方式：QQ邮箱 → 设置 → 账户 → POP3/SMTP服务 → 生成授权码
    "sender_password": "your_authorization_code",
    "receiver_email": "your_email@qq.com",
}

# ========== 数据存储 ==========
# 价格历史CSV文件路径
CSV_FILE = "price_history.csv"

# ========== 图表配置 ==========
# 价格走势图输出路径
CHART_OUTPUT = "price_chart.png"
