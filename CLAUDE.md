# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Preview HTML without sending email → writes preview.html
python main.py --dry

# Send the actual email (requires .env with SMTP vars)
python main.py
```

Requirements: `pip install -r requirements.txt` (requests, python-dotenv, mysql-connector-python).

```bash
# 初始化本地 MySQL 数据库（仅首次）
mysql -u root -p < setup_db.sql

## Architecture

Four-stage pipeline in `main.py`:

```
fetch_report() → save_report() → render_html() → send_email()
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

### Store layer (`src/db_store.py`)

Persists the normalized report dict into a local MySQL database. **Fail-safe**: DB connection errors are logged but never block email delivery.

Database `aihot`, three tables (see `setup_db.sql`):

| Table | Purpose | Key columns |
|-------|---------|-------------|
| `daily_reports` | One row per report date | `report_date` (UNIQUE), `lead_text`, `total_items` |
| `report_items` | Individual news items within sections | `report_date`, `section`, `title`, `summary`, `url` |
| `report_flashes` | Flash/brief news items | `report_date`, `title`, `source`, `url` |

Dedup: `INSERT ON DUPLICATE KEY UPDATE` for the main table; `DELETE` + re-insert for items/flashes — so re-running on the same date always reflects the latest fetch without duplicates.

## Configuration

All SMTP settings via environment variables (`.env` for local, GitHub Secrets for production):

- `SMTP_HOST` / `SMTP_PORT` (default 587)
- `SMTP_USER` / `SMTP_PASS`
- `TO_EMAIL` / `FROM_EMAIL` (optional, defaults to SMTP_USER)
- `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASS` / `DB_NAME` — defaults to `root@localhost:3306/aihot`, all optional

## GitHub Actions

- Schedule: `0 1 * * *` (UTC 01:00 = Beijing 09:00)
- Manual trigger: `workflow_dispatch` on the Actions tab
- Timeout: 5 minutes
- If daily API returns 404, falls back to items API automatically

## Network note

HTTPS (port 443) to GitHub is unreachable from the development environment; SSH (port 22) works. Always use `git@github.com` SSH remotes, never HTTPS.

## Video project (`video/`)

Remotion-based explainer video for the AI HOT project. Generates a ~5-minute 1920×1080 30fps MP4 with 3D background, AI voiceover, and animated subtitles.

```bash
cd video
npm install   # first time only

# Generate Chinese voiceover (Edge TTS, free)
python scripts/generate_audio_edge.py

# Live preview in Remotion Studio
npm run dev

# Render final MP4 (requires --gl=angle on Windows)
npx remotion render AihotIntro out/video.mp4 --gl=angle
```

### Video architecture

Audio-driven scene switching — `audioConfig.ts` is the single source of truth for timing:

```
scripts/script.json         →  human-written script (edit text here)
  ↓ gen_subtitles.py + generate_audio_edge.py
  ↓
src/audioConfig.ts          →  scene durations (from MP3 lengths) + transition config
src/subtitles.ts            →  119 subtitle entries with startFrame/endFrame
  ↓
src/AihotIntro.tsx          →  main component: scenes + subtitles + transitions
src/Background3D.tsx        →  3D wireframe torus + particles (Three.js)
src/Root.tsx                →  Remotion composition registration
```

### Video workflow

1. **Edit script**: modify `scripts/script.json` (add/remove/edit scenes and their text)
2. **Regenerate audio**: `python scripts/generate_audio_edge.py` (uses `zh-CN-YunyangNeural` voice)
3. **Regenerate subtitles**: `python scripts/gen_subtitles.py` (splits text by punctuation, distributes across scene duration)
4. **Update audioConfig.ts**: paste the MP3 durations from the audio generation output
5. **Preview**: `npm run dev` (opens Remotion Studio in browser)
6. **Render**: `npx remotion render AihotIntro out/video.mp4 --gl=angle`

### Video style

- **v3 (current)**: Minimal dark tech style — `#080810` background, gray-blue text (`#a0a5aa`), cyan accents (`#82c8d2`), soft fade transitions, bottom subtitles
- **3D background**: Two rotating wireframe torus rings + 40 floating particles, subtle opacity
- **BGM**: Synthetic beat (`public/audio/bgm.wav`), generated as fallback when Pixabay download fails
