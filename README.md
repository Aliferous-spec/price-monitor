# 商品价格监控工具

自动监控商品价格变化，降价时发送邮件通知。

## 功能

- 自动抓取商品价格
- 历史价格 CSV 存储
- 邮件降价提醒
- 定时自动运行
- 价格走势图表

## 技术栈

Python · requests · BeautifulSoup · smtplib · schedule · matplotlib

## 项目结构

```
price-monitor/
├── main.py              # 主程序入口
├── price_scraper.py     # 价格抓取模块
├── price_store.py       # CSV 数据存储
├── email_notifier.py    # 邮件通知模块
├── chart_generator.py   # 图表生成模块
├── config.py            # 配置文件
├── requirements.txt     # 依赖清单
└── README.md            # 项目说明
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

编辑 `config.py`：

- **PRODUCTS**：添加要监控的商品（名称、URL、CSS选择器）
- **EMAIL_CONFIG**：填写邮箱 SMTP 信息
  - QQ邮箱需使用授权码（QQ邮箱 → 设置 → 账户 → POP3/SMTP服务 → 生成授权码）
- **CHECK_INTERVAL_MINUTES**：设置检查间隔

### 3. 运行

```bash
# 运行一次检查
python main.py

# 测试邮件配置
python main.py --test-email

# 启动定时监控
python main.py --schedule
```

## 配置示例

添加京东商品：

```python
PRODUCTS = [
    {
        "name": "iPhone 16",
        "url": "https://item.jd.com/100012345678.html",
        "css_selector": "span.price",
        "target_price": 5000.0,  # 降到5000以下通知
    },
]
```

## 许可证

MIT
