# 🔍 Price Monitor

一个轻量级 Python 价格监控工具 — 自动抓取商品页面、记录价格历史、在降价时发送通知。

## 架构

```
price-monitor/
├── main.py             # 入口：配置加载 + 主循环
├── scraper.py          # 网页抓取 & 价格解析
├── storage.py          # 数据持久化 & 历史查询
├── notifier.py         # 通知渠道（邮件 / Telegram）
├── demo.py             # 一键验证三个模块是否正常
├── config.example.py   # 配置文件模板
└── requirements.txt    # 依赖
```

三个核心模块各司其职：

| 模块 | 职责 |
|------|------|
| `scraper.py` | HTTP 请求（含重试）、CSS 选择器解析、多地区价格格式归一化 |
| `storage.py` | JSON-lines 持久化、历史最低价查询、降价检测 |
| `notifier.py` | 可插拔的通知渠道（已内置 Email + Telegram），注册即用 |

## 运行效果

```terminal
$ python demo.py

============================================================
  1. SCRAPER — 测试价格提取
============================================================
  ✓  '$19.99'             →      19.99  (expected 19.99)
  ✓  '1.299,99 €'         →    1299.99  (expected 1299.99)
  ✓  '¥ 299.00'           →     299.00  (expected 299.0)
  ✓  '1,999.99'           →    1999.99  (expected 1999.99)

  → 从 HTML 提取价格: ¥199.99

============================================================
  2. STORAGE — 测试数据持久化
============================================================
  已存储 3 条价格记录:
    2026-07-02T09:30:00  ¥259.00
    2026-07-02T09:30:00  ¥249.00
    2026-07-02T09:30:00  ¥239.00

  📉 历史最低: ¥239.00
  📉 价格下降检测 (¥229 vs 上次 ¥239.0): True

============================================================
  3. NOTIFIER — 已注册的通知渠道
============================================================
  🔔 email
  🔔 telegram

============================================================
  ✅ 三大模块就绪: scraper · storage · notifier
============================================================
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 创建配置文件

```bash
cp config.example.py config.py
```

编辑 `config.py`，至少填写两项：

```python
TARGET_URL   = "https://item.jd.com/100012345678.html"   # 商品链接
CSS_SELECTOR = ".price-box .price"                       # 价格元素的 CSS 选择器
```

### 3. 验证环境

```bash
python demo.py
```

全部 ✓ 即可进入下一步。

### 4. 启动监控

```bash
python main.py
```

程序会按 `CHECK_INTERVAL`（默认 3600 秒）循环检查价格，并在满足条件时发送通知。

## 配置说明

| 配置项 | 类型 | 说明 |
|--------|------|------|
| `TARGET_URL` | str | **必填** — 商品页面 URL |
| `CSS_SELECTOR` | str | **必填** — 价格元素的 CSS 选择器 |
| `PRICE_REGEX` | str | 可选 — 用正则从元素文本中提取数字 |
| `CHECK_INTERVAL` | int | 检查间隔（秒），默认 3600 |
| `PRICE_THRESHOLD` | float | 价格阈值，低于此值触发通知 |
| `HISTORY_FILE` | str | 历史记录文件路径，默认 `price_history.jsonl` |
| `EMAIL_RECIPIENT` | str | 邮件接收地址 |
| `SMTP_SERVER` | str | SMTP 服务器地址 |
| `SMTP_PORT` | int | SMTP 端口 |
| `SMTP_USER` | str | SMTP 登录用户名 |
| `SMTP_PASSWORD` | str | SMTP 密码（Gmail 需应用专用密码） |
| `TELEGRAM_BOT_TOKEN` | str | Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | str | Telegram 对话 ID |

> **提示**：也可以使用 `.env` 文件配置，环境变量优先级高于 `config.py`。

## 触发通知的条件

以下任一条件满足时，程序会通过已配置的所有渠道发送通知：

1. **价格跌破阈值** — 当前价格 ≤ `PRICE_THRESHOLD`
2. **价格较上次下降** — 当前价格 < 历史记录中最近一次价格

## 历史记录

价格记录存储在 JSON-lines 文件中（默认 `price_history.jsonl`），每行一条：

```json
{"timestamp": "2026-07-02T09:30:00+00:00", "url": "https://...", "price": 239.0, "currency": "CNY"}
```

可以直接用文本编辑器查看，或用 `storage.load_history()` 在代码中读取。

## 扩展通知渠道

`notifier.py` 使用注册器模式，添加新渠道只需在模块中定义一个函数并注册：

```python
from notifier import register

@register("wechat")
def send_wechat(config: dict, subject: str, body: str) -> bool:
    # 你的企业微信 / Server 酱 逻辑
    ...
    return True
```

## License

MIT
