# Price Monitor — 项目架构与模块设计

## 概述

Price Monitor 是一个轻量级 Python 价格监控工具，能够自动抓取商品页面、持久化价格历史、在降价或触及阈值时发送多渠道通知，并生成价格走势可视化图表。

## 架构总览

```
config.py          .env (可选)
     │                 │
     └────────┬────────┘
              ▼
         main.py  ──────────── 主循环入口
         ┌───┼───┐
         │   │   │
    ┌────▼┐ ┌▼───▼──┐ ┌──────────▼──┐
    │scraper│ │storage│ │ notifier    │
    │ .py   │ │.py    │ │ .py         │
    └───────┘ └───────┘ └─────────────┘
         │        │            │
         │   price_history     │
         │   .jsonl            │
         │        │            │
         │   ┌────▼─────┐      │
         │   │visualiz-  │      │
         │   │ation.py   │      │
         │   └───────────┘      │
         │        │             │
         │   price_chart.png    │
         │                      │
         ▼                      ▼
     目标网站              Email / Telegram
```

## 数据流

```
[定时触发]
    │
    ▼
scraper.get_current_price(url, selector)
    │  HTTP GET → BeautifulSoup 解析 → CSS 选择器提取 → 价格归一化
    │  返回: float | None
    ▼
storage.save_record(PriceRecord)
    │  JSON-lines 追加写入 price_history.jsonl
    ▼
判断是否告警:
    ├── price ≤ PRICE_THRESHOLD  →  触发告警
    └── price < 上次记录         →  触发告警
    │
    ▼ (告警时)
notifier.notify(config, subject, body)
    │  遍历 NOTIFIERS 注册表 → 分发到 email / telegram
    ▼
sleep(CHECK_INTERVAL) → 下一轮循环
```

## 模块说明

### 1. `main.py` — 主入口 & 调度器

**职责：** 程序启动、配置加载、主循环编排、异常兜底。

- `_load_config()` — 优先从 `config.py` 导入配置，再用环境变量覆盖（env var 优先级更高）。支持 `python-dotenv` 自动加载 `.env` 文件。
- `_validate_config()` — 校验 `TARGET_URL` 和 `CSS_SELECTOR` 为必填；对 `CHECK_INTERVAL`、`PRICE_THRESHOLD` 做类型归一化。
- `check_once()` — 单次检查周期：抓取 → 存储 → 判断 → 告警，返回 `PriceRecord | None`。
- `main()` — 无限循环主函数。内置连续异常计数器（默认 5 次上限），超过后自动退出防止空转。捕获 `KeyboardInterrupt` 优雅退出。

### 2. `scraper.py` — 页面抓取 & 价格提取

**职责：** HTTP 请求 + HTML 解析 + 价格数字提取与归一化。

核心函数：

| 函数 | 说明 |
|---|---|
| `fetch_page(url, ...)` | 带重试的 HTTP GET，支持超时 / 连接错误 / HTTP 状态错误的分类处理。4xx 不重试直接抛出，5xx 和网络错误指数退避重试（默认 3 次）。 |
| `parse_price(html, selector, ...)` | 用 BeautifulSoup + CSS 选择器定位价格元素，正则提取数字。选择器匹配失败时自动扫描页面输出候选元素（`_dump_price_candidates`），辅助排查页面结构变更。 |
| `get_current_price(url, selector, ...)` | `fetch_page` + `parse_price` 的一站式封装。 |
| `_normalise_price(raw)` | 地区格式自适应：智能识别 `1.299,99`（欧洲）与 `1,299.99`（美式），统一转为 `float`。 |

**错误处理层次：**
1. 网络超时 → 重试 + 诊断建议
2. 连接失败（DNS/拒绝连接/断网）→ 重试 + 诊断建议
3. HTTP 4xx → 不重试，直接抛出
4. HTTP 5xx → 重试
5. CSS 选择器无匹配 → 扫描候选元素，提示更新配置
6. 正则不匹配 → 提示价格格式变更或配置 `PRICE_REGEX`

### 3. `storage.py` — 数据持久化

**职责：** 价格记录的存储与查询，基于 JSON-lines 文件格式。

**数据模型：**
```python
@dataclass
class PriceRecord:
    timestamp: str    # ISO-8601 UTC
    url: str
    price: float
    currency: str     # 默认 "CNY"
```

**设计决策：** 选用 JSON-lines（每行一个 JSON 对象）而非 SQLite：
- 人类可读，可用任何文本编辑器查看
- 追加写入无锁竞争（单写入者场景）
- 易于用 `grep` / `jq` 等命令行工具分析
- 与 `visualization.py` 共享同一数据格式

核心函数：

| 函数 | 说明 |
|---|---|
| `save_record(record, filepath)` | 追加一条记录到 JSON-lines 文件 |
| `load_history(filepath)` | 读取全部历史记录，自动跳过损坏行 |
| `get_lowest_price(filepath)` | 返回历史最低价记录 |
| `get_current_price_record(filepath)` | 返回最近一次记录 |
| `price_dropped(new_price, filepath)` | 判断新价格是否低于上次记录 |

### 4. `notifier.py` — 通知模块

**职责：** 多渠道价格告警分发，支持扩展。

**架构模式：** 注册表模式（Registry Pattern）

```python
NOTIFIERS: Dict[str, NotifierFunc] = {}

@register("email")
def send_email(config, subject, body): ...

@register("telegram")
def send_telegram(config, subject, body): ...
```

新增通知渠道只需：实现 `send_<channel>(config, subject, body) -> bool` 并用 `@register("<name>")` 注册即可，无需修改调度代码。

内置渠道：

| 渠道 | 实现 | 所需配置 |
|---|---|---|
| Email | SMTP + STARTTLS（适配 Gmail） | `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_RECIPIENT` |
| Telegram | Bot API (`sendMessage`) | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` |

`notify(config, subject, body)` — 公共 API，遍历所有已注册 notifier 并分发，单个渠道失败不影响其他渠道。

### 5. `visualization.py` — 价格走势图

**职责：** 使用 matplotlib 生成价格历史折线图。

- 支持从 JSON-lines 历史文件加载真实数据，也内置 `--demo` 模式生成 30 天模拟数据。
- 自动检测并配置中文字体（Microsoft YaHei → SimHei → PingFang SC → Noto Sans CJK SC）。
- 图表元素：价格主线 + 面积填充 + 7 日移动平均线 + 最低价/当前价标注 + 显著降价百分比标记 + 起始价参考线。
- 底部统计信息栏（30 天最高/最低/波动/当前）。
- CLI 接口：`--demo` / `--file` / `--output` / `--title` / `--no-ma`。

### 6. `demo.py` — 集成演示

**职责：** 无需真实配置即可验证三大核心模块（scraper / storage / notifier）功能正常。

- 测试价格归一化的多种格式
- 测试 HTML 解析提取
- 测试 JSON-lines 读写与历史查询
- 展示已注册的通知渠道

### 7. `config.example.py` — 配置模板

新用户复制为 `config.py` 并填入真实值即可使用。包含：目标 URL、CSS 选择器、检查间隔、价格阈值、邮件/Telegram 凭据。

配置优先级：**环境变量 > config.py > 默认值**

## 依赖

| 包 | 用途 |
|---|---|
| `requests` | HTTP 请求 |
| `beautifulsoup4` | HTML 解析 |
| `python-dotenv` | .env 文件加载（可选） |
| `matplotlib` | 价格走势图 |
| `numpy` | 移动平均计算 |

## 设计原则

1. **单一职责：** 每个 `.py` 文件只负责一个清晰的领域（抓取 / 存储 / 通知 / 可视化），可独立使用或测试。
2. **渐进增强：** 核心功能只需 `TARGET_URL` + `CSS_SELECTOR` 即可运行；通知、可视化均为可选模块。
3. **防御性编程：** 每个环节都有错误处理与诊断日志，单次失败不影响后续周期；选择器失效时自动输出页面候选元素辅助排查。
4. **可扩展：** 通知渠道通过 `@register` 装饰器注册，无需改动调度逻辑；价格提取支持自定义正则 `PRICE_REGEX`。
5. **无状态进程：** 所有状态持久化在 `price_history.jsonl` 文件中，进程可随时重启而不丢失历史。
