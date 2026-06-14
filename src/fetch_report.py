"""
AI HOT 数据拉取模块。

策略：
  1. 优先拉 `/api/public/daily`（编辑成品日报）
  2. 如果当天日报尚未生成（404），降级到
     `/api/public/items?mode=selected&since=<24h 前>`
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://aihot.virxact.com"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 aihot-skill/0.2.0"
)

# 北京时间 = UTC+8
BEIJING_TZ = timezone(timedelta(hours=8))

# items API 的 category slug → 中文标签
CATEGORY_LABELS = {
    "ai-models":  "模型发布/更新",
    "ai-products": "产品发布/更新",
    "industry":   "行业动态",
    "paper":      "论文研究",
    "tip":        "技巧与观点",
}

SECTION_ORDER = [
    "模型发布/更新",
    "产品发布/更新",
    "行业动态",
    "论文研究",
    "技巧与观点",
]


def _beijing_now() -> datetime:
    """返回当前北京时间。"""
    return datetime.now(timezone.utc).astimezone(BEIJING_TZ)


def _iso_to_beijing(iso_str: Optional[str]) -> str:
    """把 ISO 8601 UTC 字符串转为北京时间可读格式。"""
    if not iso_str:
        return ""
    try:
        dt_utc = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        dt_bj = dt_utc.astimezone(BEIJING_TZ)
        now = _beijing_now()
        diff = now - dt_bj
        if diff < timedelta(hours=1):
            return f"{int(diff.total_seconds() // 60)} 分钟前"
        if diff < timedelta(hours=24) and now.date() == dt_bj.date():
            return f"今天 {dt_bj.strftime('%H:%M')}"
        if diff < timedelta(hours=48) and (now - timedelta(days=1)).date() == dt_bj.date():
            return f"昨天 {dt_bj.strftime('%H:%M')}"
        return dt_bj.strftime("%m/%d %H:%M")
    except (ValueError, TypeError):
        return iso_str


def fetch_daily(date_str: Optional[str] = None) -> Optional[dict]:
    """
    拉取 AI HOT 日报。

    Args:
        date_str: 可选，YYYY-MM-DD；不传则拉最新日报。

    Returns:
        日报 dict（含 date / lead / sections / flashes），
        如果 404 返回 None。
    """
    if date_str:
        url = f"{BASE_URL}/api/public/daily/{date_str}"
    else:
        url = f"{BASE_URL}/api/public/daily"

    logger.info("Fetching daily: %s", url)
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=30)

    if resp.status_code == 404:
        logger.warning("Daily not available (404): %s", url)
        return None
    resp.raise_for_status()
    return resp.json()


def fetch_items(since_hours: int = 24) -> dict:
    """
    拉取精选条目（daily 不可用时的降级路径）。

    Args:
        since_hours: 拉最近多少小时的数据，默认 24。

    Returns:
        items API 响应 dict。
    """
    since = (datetime.now(timezone.utc) - timedelta(hours=since_hours))
    since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    url = (
        f"{BASE_URL}/api/public/items"
        f"?mode=selected&since={since_str}&take=60"
    )
    logger.info("Fetching items (fallback): %s", url)
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ---------- 归一化 ----------

def normalize_daily(daily: dict) -> dict:
    """
    把 daily API 返回归一化成统一的中间结构。
    """
    sections: list[dict] = []
    total = 0
    for sec in daily.get("sections", []):
        label = sec.get("label", "其他")
        items = []
        for item in sec.get("items", []):
            items.append({
                "title":   item.get("title", ""),
                "summary": item.get("summary", ""),
                "url":     item.get("sourceUrl", ""),
                "source":  item.get("sourceName", ""),
                "time_str": "",  # daily 里的 item 没有独立时间
            })
        sections.append({"label": label, "items": items})
        total += len(items)

    # 快讯
    flashes = []
    for f in daily.get("flashes", []):
        flashes.append({
            "title":   f.get("title", ""),
            "source":  f.get("sourceName", ""),
            "url":     f.get("sourceUrl", ""),
            "time_str": _iso_to_beijing(f.get("publishedAt")),
        })

    lead_text = ""
    lead = daily.get("lead")
    if lead:
        lead_text = lead.get("leadParagraph", "") or lead.get("title", "") or ""

    return {
        "date":      daily.get("date", ""),
        "lead":      lead_text,
        "sections":  sections,
        "flashes":   flashes,
        "total":     total,
    }


def normalize_items(data: dict) -> dict:
    """
    把 items API 返回归一化成统一的中间结构。

    按 category 分组 → 5 个 section。
    """
    groups: dict[str, list] = {label: [] for label in SECTION_ORDER}
    groups["其他"] = []
    total = 0

    for item in data.get("items", []):
        cat = item.get("category") or ""
        label = CATEGORY_LABELS.get(cat, "其他")
        entry = {
            "title":    item.get("title", ""),
            "summary":  item.get("summary", ""),
            "url":      item.get("url", ""),
            "source":   item.get("source", ""),
            "time_str": _iso_to_beijing(item.get("publishedAt")),
        }
        groups.setdefault(label, []).append(entry)
        total += 1

    sections = []
    for label in SECTION_ORDER:
        items = groups.get(label, [])
        if items:
            sections.append({"label": label, "items": items})

    # 兜底：其他分类
    others = groups.get("其他", [])
    if others:
        sections.append({"label": "其他", "items": others})

    today_str = _beijing_now().strftime("%Y-%m-%d")

    return {
        "date":      today_str,
        "lead":      "",
        "sections":  sections,
        "flashes":   [],
        "total":     total,
    }


def fetch_report() -> dict:
    """
    拉取今日 AI HOT 内容的统一入口。

    Returns:
        归一化 dict：{ date, lead, sections, flashes, total }
    """
    daily = fetch_daily()
    if daily is not None:
        logger.info("Using daily report.")
        return normalize_daily(daily)

    logger.info("Daily not ready; falling back to items API.")
    items_data = fetch_items(since_hours=24)
    return normalize_items(items_data)
