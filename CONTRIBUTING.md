# Contributing to Price Monitor

Thanks for your interest in contributing! This document outlines the conventions and workflow to follow.

## Setup

```bash
# 1. Clone & enter the project
git clone https://github.com/Aliferous-spec/price-monitor.git
cd price-monitor

# 2. Create a virtual environment (Python 3.9+)
python -m venv .venv
source .venv/bin/activate   # Linux / macOS
.venv\Scripts\activate      # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create a local config (not tracked by git)
cp config.example.py config.py

# 5. Verify everything works
python demo.py
```

> `config.py` is git-ignored — never commit secrets. Use `config.example.py` as a template for new config keys.

## Project architecture

```
price-monitor/
├── main.py             # Entry point — config loading, main loop, alert logic
├── scraper.py          # HTTP fetch + CSS-selector price extraction
├── storage.py          # JSON-lines persistence, history queries, drop detection
├── notifier.py         # Pluggable notification channels (email, Telegram, …)
├── visualization.py    # matplotlib chart rendering
├── demo.py             # One-shot smoke test of scraper / storage / notifier
├── config.example.py   # Config template (copy → config.py)
└── requirements.txt    # Third-party dependencies
```

The three core modules (`scraper`, `storage`, `notifier`) are independent — each can be tested in isolation via `demo.py`.

## Coding conventions

- **Python 3.9+** with `from __future__ import annotations` for modern type hints.
- Use **type annotations** on all public functions.
- Follow [PEP 8](https://peps.python.org/pep-0008/) — 4 spaces, 100-char lines.
- Docstrings use **Google style** (triple-quote, `Args:` / `Returns:` sections).
- Keep dependencies minimal — `requests`, `beautifulsoup4`, `python-dotenv`, `matplotlib`, `numpy`. Justify any new dependency.
- Config keys are `UPPER_SNAKE_CASE`; all are read from `config.py` with env-var overrides.

## Adding a notification channel

`notifier.py` uses a **register decorator** — adding a new channel is two steps:

```python
# In notifier.py (or a new file you import from notifier.py)
from notifier import register

@register("slack")
def send_slack(config: dict, subject: str, body: str) -> bool:
    """Send a price alert to a Slack webhook."""
    webhook_url = config.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return False
    # … your webhook logic …
    return True
```

- The function name doesn't matter — the `@register("name")` string is the channel key.
- Return `True` on success, `False` on failure.
- If the required config keys are missing, return `False` silently (the caller handles it).
- Add any new config keys to `config.example.py` with comments.

## Adding a scraper backend

The default scraper uses `requests` + `BeautifulSoup` + a CSS selector. If you want to add a different backend (Playwright, Selenium, an API client):

1. Add a new module (e.g. `scraper_playwright.py`) with a function matching the `get_current_price(url, selector, **kwargs) -> float | None` signature.
2. Wire it into `main.py` behind a config flag (`SCRAPER_BACKEND = "playwright"`).
3. Update `demo.py` to exercise the new backend.

## Before submitting a PR

1. **Run `demo.py`** — all three checks must pass.
2. **Test any new notifier** with a real config (even just once).
3. **Update `config.example.py`** if you added config keys.
4. **Update `README.md`** if the change affects user-facing behaviour.
5. **Keep commits focused** — one logical change per commit, with a clear message.

## Commit messages

Write commits in the present tense, starting with a lowercase verb:

```
add Slack notifier channel
fix price regex for European formats
update README with Telegram setup steps
```

## Reporting issues

Please include:

- **What you did** — the command or code that triggered the problem.
- **What you expected** — the behaviour you wanted.
- **What happened** — the actual output, error message, or unexpected result.
- **Environment** — OS, Python version (`python --version`), and the target website (if relevant).

## License

By contributing, you agree that your code will be licensed under the same [MIT License](LICENSE) as the project.
