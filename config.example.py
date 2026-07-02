# ============================================================
# Price Monitor — 配置文件示例
# 复制为 config.py 并填入真实值后即可使用
# ============================================================

# --- 目标商品 -------------------------------------------------
TARGET_URL = "https://item.jd.com/100012345678.html"   # 商品页面 URL
CSS_SELECTOR = ".price-box .price"                     # 价格元素的 CSS 选择器
# PRICE_REGEX = r"(\d+\.\d{2})"                        # （可选）用正则提取数字

# --- 监控频率（秒）---------------------------------------------
CHECK_INTERVAL = 3600  # 每小时检查一次

# --- 价格阈值 -------------------------------------------------
PRICE_THRESHOLD = 99.99  # 低于此价格时发送通知

# --- 历史记录 -------------------------------------------------
HISTORY_FILE = "price_history.jsonl"

# --- 邮件通知（可选）--------------------------------------------
EMAIL_RECIPIENT = "your_email@example.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "your_email@gmail.com"
SMTP_PASSWORD = "your_app_password"    # Gmail 应用专用密码

# --- Telegram 通知（可选）--------------------------------------
# TELEGRAM_BOT_TOKEN = "123456:ABC-DEF1234gh..."
# TELEGRAM_CHAT_ID = "123456789"
