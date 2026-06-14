# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Preview HTML without sending email → writes preview.html
python main.py --dry

# Send the actual email (requires .env with SMTP vars)
python main.py
```

Requirements: `pip install -r requirements.txt` (requests, python-dotenv).

## Architecture

Three-stage pipeline in `main.py`:

```
fetch_report() → render_html() → send_email()
```

### Data layer (`src/fetch_report.py`)

Two data sources, one unified output. `fetch_report()` tries daily first, falls back to items on 404:

| Priority | API endpoint | When |
|----------|-------------|------|
| 1 | `/api/public/daily` | Normal path — editor-curated daily report |
| 2 | `/api/public/items?mode=selected&since=<24h>` | Daily not yet generated (before 08:00 Beijing) |

Both paths normalize into the same intermediate dict shape:
```python
{
    "date": "2026-06-14",
    "lead": "主编点评 text or empty",
    "sections": [{"label": "模型发布/更新", "items": [...]}, ...],
    "flashes": [{"title", "source", "url", "time_str"}, ...],
    "total": 11
}
```

`normalize_daily()` handles the daily endpoint's structure (items nested under `sourceUrl`/`sourceName` keys, flashes separate). `normalize_items()` handles the items endpoint's flat list, grouping by `category` slug into the 5 standard section labels.

API requires a browser User-Agent header (`aihot-skill/0.2.0` identifier) to bypass nginx bot blocking.

### Render layer (`src/render_email.py`)

Produces a self-contained HTML email (no external CSS/images). Design constraints:
- **Inline CSS only** — email clients strip `<style>` blocks and external stylesheets
- Color theme defined as a `STYLE` dict at module level — to change colors, edit the dict values (currently dark gray `#1a1a2e`)
- Sections rendered in fixed order with matching icons: 模型/产品/行业/论文/技巧
- Global sequential numbering across all sections (not reset per section)
- `_iso_to_beijing()` in fetch_report.py converts UTC timestamps to human-readable Beijing time ("今天 09:48", "昨天 14:30")

### Send layer (`src/send_email.py`)

SMTP via environment variables. Port 465 → SSL, all others → STARTTLS. Fails with Chinese-language error messages for auth/connection failures.

## Configuration

All SMTP settings via environment variables (`.env` for local, GitHub Secrets for production):

- `SMTP_HOST` / `SMTP_PORT` (default 587)
- `SMTP_USER` / `SMTP_PASS`
- `TO_EMAIL` / `FROM_EMAIL` (optional, defaults to SMTP_USER)

## GitHub Actions

- Schedule: `0 1 * * *` (UTC 01:00 = Beijing 09:00)
- Manual trigger: `workflow_dispatch` on the Actions tab
- Timeout: 5 minutes
- If daily API returns 404, falls back to items API automatically

## Network note

HTTPS (port 443) to GitHub is unreachable from the development environment; SSH (port 22) works. Always use `git@github.com` SSH remotes, never HTTPS.
