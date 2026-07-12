"""
generate_demo_gif.py — creates a feature demo GIF for the Price Monitor README.

Uses Pillow to render terminal-style frames showing the demo.py output
and the price chart visualization, then combines them into an animated GIF.
"""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OUTPUT = "demo.gif"
CHART_PATH = "price_chart.png"
FRAME_W, FRAME_H = 800, 520
TERMINAL_BG = "#1E1E2E"
TERMINAL_FG = "#CDD6F4"
GREEN = "#A6E3A1"
YELLOW = "#F9E2AF"
BLUE = "#89B4FA"
RED = "#F38BA8"
CYAN = "#94E2D5"
ORANGE = "#FAB387"
DIM = "#6C7086"
WHITE = "#FFFFFF"
TITLE_BG = "#0D1117"
ACCENT = "#2B6CB0"

FONT_BOLD = None
FONT_REGULAR = None
FONT_MONO = None

# ---------------------------------------------------------------------------
# Font loading
# ---------------------------------------------------------------------------

def _load_fonts():
    """Try to load reasonable fonts; fall back to default."""
    global FONT_BOLD, FONT_REGULAR, FONT_MONO

    win_fonts = "C:/Windows/Fonts"

    # Mono font candidates (use full paths on Windows)
    candidates_mono = [
        os.path.join(win_fonts, "consola.ttf"),
        os.path.join(win_fonts, "cour.ttf"),
        "Cascadia Code", "Cascadia Mono", "Consolas", "Courier New",
        "JetBrains Mono", "Fira Code",
    ]
    # Sans/CJK font candidates
    candidates_sans = [
        os.path.join(win_fonts, "msyh.ttc"),
        os.path.join(win_fonts, "msyhbd.ttf"),
        os.path.join(win_fonts, "simhei.ttf"),
        "Microsoft YaHei", "SimHei",
        "Segoe UI", "PingFang SC", "Noto Sans", "DejaVu Sans",
    ]

    # Find a working mono font
    for name in candidates_mono:
        try:
            test = ImageFont.truetype(name, 14)
            FONT_MONO = name
            break
        except (OSError, IOError):
            continue
    if FONT_MONO is None:
        FONT_MONO = ""

    # Find a working sans font (for Chinese labels)
    for name in candidates_sans:
        try:
            test = ImageFont.truetype(name, 14)
            FONT_REGULAR = name
            break
        except (OSError, IOError):
            continue
    if FONT_REGULAR is None:
        FONT_REGULAR = ""

    FONT_BOLD = FONT_REGULAR

    print(f"Fonts loaded — mono: {FONT_MONO}, sans: {FONT_REGULAR}")


def _mono(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(FONT_MONO, size) if FONT_MONO else ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()


def _sans(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(FONT_REGULAR, size) if FONT_REGULAR else ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Frame builders
# ---------------------------------------------------------------------------

def _terminal_frame(lines: list[tuple[str, str]]) -> Image.Image:
    """Create a terminal-style frame.

    Args:
        lines: List of (text, color) tuples. Empty string = blank line.
    """
    img = Image.new("RGB", (FRAME_W, FRAME_H), TERMINAL_BG)
    draw = ImageDraw.Draw(img)
    font = _mono(13)

    # Window title bar
    draw.rectangle([(0, 0), (FRAME_W, 32)], fill="#181825")
    # Dots
    for i, color in enumerate(["#F38BA8", "#F9E2AF", "#A6E3A1"]):
        draw.ellipse([(12 + i * 22, 10), (24 + i * 22, 22)], fill=color)
    draw.text((80, 5), "Terminal — Price Monitor Demo", fill=DIM, font=_mono(11))

    y = 46
    for text, color in lines:
        if text == "":
            y += 16
            continue
        draw.text((24, y), text, fill=color, font=font)
        y += 20
        if y > FRAME_H - 20:
            break

    return img


def _title_frame(title: str, subtitle: str) -> Image.Image:
    """Create a title/hero frame."""
    img = Image.new("RGB", (FRAME_W, FRAME_H), TITLE_BG)
    draw = ImageDraw.Draw(img)

    # Decorative top bar
    draw.rectangle([(0, 0), (FRAME_W, 4)], fill=ACCENT)

    # Icon / emoji
    font_large = _sans(56)
    draw.text((FRAME_W // 2, 120), "🔍", fill=WHITE, font=font_large, anchor="mm")

    # Title
    font_title = _sans(36)
    draw.text((FRAME_W // 2, 210), title, fill=WHITE, font=font_title, anchor="mm")

    # Accent line
    draw.rectangle(
        [(FRAME_W // 2 - 60, 245), (FRAME_W // 2 + 60, 248)],
        fill=ACCENT,
    )

    # Subtitle
    font_sub = _sans(17)
    draw.text((FRAME_W // 2, 290), subtitle, fill=DIM, font=font_sub, anchor="mm")

    # Bottom hint
    font_hint = _sans(13)
    draw.text(
        (FRAME_W // 2, FRAME_H - 50),
        "github.com/Aliferous-spec/price-monitor",
        fill="#30363D",
        font=font_hint,
        anchor="mm",
    )

    return img


def _chart_frame() -> Image.Image:
    """Frame showing the generated price chart."""
    img = Image.new("RGB", (FRAME_W, FRAME_H), TITLE_BG)
    draw = ImageDraw.Draw(img)

    # Top header
    draw.rectangle([(0, 0), (FRAME_W, 40)], fill="#161B22")
    draw.text((20, 8), "📈 价格走势可视化", fill=WHITE, font=_sans(16))

    # Load and paste chart
    if os.path.isfile(CHART_PATH):
        chart = Image.open(CHART_PATH)
        # Scale to fit (preserve aspect ratio)
        max_w, max_h = FRAME_W - 40, FRAME_H - 80
        ratio = min(max_w / chart.width, max_h / chart.height)
        new_w, new_h = int(chart.width * ratio), int(chart.height * ratio)
        chart = chart.resize((new_w, new_h), Image.LANCZOS)

        # Center it
        x = (FRAME_W - new_w) // 2
        y = 50
        img.paste(chart, (x, y))

    # Bottom caption
    draw.text(
        (FRAME_W // 2, FRAME_H - 22),
        "python visualization.py --demo    →    price_chart.png",
        fill=DIM,
        font=_mono(12),
        anchor="mm",
    )

    return img


def _main_loop_frame() -> Image.Image:
    """Frame showing the monitor running."""
    lines = [
        ("$ python main.py", WHITE),
        ("", ""),
        ("2026-07-12 10:30:00 [INFO] 🚀 Price Monitor started", BLUE),
        ("  checking https://item.jd.com/demo every 3600s", DIM),
        ("  Notifiers enabled: email, telegram", DIM),
        ("", ""),
        ("2026-07-12 10:30:01 [INFO] 当前价格: ¥379.00", GREEN),
        ("2026-07-12 10:30:01 [INFO] 已保存到 price_history.jsonl", GREEN),
        ("", ""),
        ("2026-07-12 10:30:01 [INFO] 📉 价格下降检测: True", YELLOW),
        ("2026-07-12 10:30:01 [INFO] 🔔 发送邮件通知 → target@email.com", CYAN),
        ("2026-07-12 10:30:02 [INFO] 🔔 发送 Telegram 通知 → @user", CYAN),
        ("", ""),
        ("2026-07-12 10:30:02 [INFO] Next check in 3600s ...", DIM),
        ("", ""),
        ("  ████████████████░░░░  监控中...", GREEN),
    ]
    return _terminal_frame(lines)


# ---------------------------------------------------------------------------
# GIF assembly
# ---------------------------------------------------------------------------

def create_demo_gif() -> str:
    """Build the full demo GIF and return the output path."""
    _load_fonts()

    # --- Regenerate chart first (ensure it's fresh) ---
    # (Already done by this point — assume price_chart.png exists)

    frames: list[Image.Image] = []

    # Frame 1: Title  (2.5s)
    frames.append(_title_frame(
        "Price Monitor",
        "轻量级 Python 价格监控工具",
    ))

    # Frame 2-4: Demo output, each section highlighted (1.8s each)
    scraper = [
        ("$ python demo.py", WHITE),
        ("=" * 60, DIM),
        ("  1. SCRAPER — 测试价格提取", BLUE),
        ("=" * 60, DIM),
        ("", ""),
        ("  ✓  '$19.99'             →      19.99  (expected 19.99)", GREEN),
        ("  ✓  '1.299,99 €'         →    1299.99  (expected 1299.99)", GREEN),
        ("  ✓  '¥ 299.00'           →     299.00  (expected 299.0)", GREEN),
        ("  ✓  '1,999.99'           →    1999.99  (expected 1999.99)", GREEN),
        ("", ""),
        ("  → 从 HTML 提取价格: ¥199.99", CYAN),
        ("", ""),
        ("  4/4 测试通过 ✅", GREEN),
    ]
    frames.append(_terminal_frame(scraper))

    storage = [
        ("$ python demo.py", WHITE),
        ("=" * 60, DIM),
        ("  2. STORAGE — 测试数据持久化", BLUE),
        ("=" * 60, DIM),
        ("", ""),
        ("  已存储 3 条价格记录:", DIM),
        ("    2026-07-02T09:30:00  ¥259.00", WHITE),
        ("    2026-07-02T09:30:00  ¥249.00", WHITE),
        ("    2026-07-02T09:30:00  ¥239.00", WHITE),
        ("", ""),
        ("  📉 历史最低: ¥239.00", GREEN),
        ("  📉 价格下降检测 (¥229 vs 上次 ¥239.0): True", GREEN),
        ("", ""),
        ("  持久化 & 查询正常 ✅", GREEN),
    ]
    frames.append(_terminal_frame(storage))

    notifier = [
        ("$ python demo.py", WHITE),
        ("=" * 60, DIM),
        ("  3. NOTIFIER — 已注册的通知渠道", BLUE),
        ("=" * 60, DIM),
        ("", ""),
        ("  🔔 email       — SMTP 邮件通知", GREEN),
        ("  🔔 telegram    — Bot API 推送", GREEN),
        ("", ""),
        ("  ℹ️  实际通知仅在配置 SMTP / Telegram Token 后触发", DIM),
        ("", ""),
        ("=" * 60, DIM),
        ("  ✅ 三大模块就绪: scraper · storage · notifier", GREEN),
        ("=" * 60, DIM),
    ]
    frames.append(_terminal_frame(notifier))

    # Frame 5: Chart (3s)
    frames.append(_chart_frame())

    # Frame 6: Monitor running (2s)
    frames.append(_main_loop_frame())

    # Frame 7: Closing card (2s)
    closing = _title_frame(
        "Price Monitor",
        "python main.py  —  开始监控你的目标商品 🛒",
    )
    frames.append(closing)

    # --- Assemble GIF ---
    durations = [
        2200,   # title
        1800,   # scraper
        1800,   # storage
        1800,   # notifier
        3000,   # chart
        2200,   # monitor
        2200,   # closing
    ]

    gif_frames = []
    for img, dur in zip(frames, durations):
        # Convert to palette mode for GIF
        gif_frames.append(img.convert("P", palette=Image.ADAPTIVE, colors=256))

    abs_output = os.path.abspath(OUTPUT)
    gif_frames[0].save(
        abs_output,
        save_all=True,
        append_images=gif_frames[1:],
        duration=durations,
        loop=0,  # infinite loop
        optimize=True,
        disposal=2,
    )

    print(f"[OK] Demo GIF created → {abs_output}")
    print(f"     {len(gif_frames)} frames, {sum(durations) / 1000:.1f}s total")
    return abs_output


if __name__ == "__main__":
    create_demo_gif()
