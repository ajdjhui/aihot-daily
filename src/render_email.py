"""
HTML 邮件渲染：把归一化的日报 dict 渲染成适合邮件发送的 HTML。

设计要点：
  - 纯内联 CSS（邮件客户端兼容）
  - 中文排版友好
  - 5 版块分组 + 全局编号
  - 响应式宽度（max 640px）
"""

import html as html_mod
import textwrap
from typing import Optional

# ---- CSS 常量 ----

# 主色调：深色文字 + 蓝色链接 + 浅灰背景
STYLE = {
    "body": (
        "margin:0;padding:0;background-color:#f5f5f5;"
        "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,"
        "'Helvetica Neue',Arial,'Noto Sans SC',sans-serif;"
        "color:#1a1a1a;line-height:1.6;"
    ),
    "container": (
        "max-width:640px;margin:0 auto;background-color:#ffffff;"
        "border-radius:12px;overflow:hidden;"
    ),
    "header": (
        "background-color:#1a1a2e;"
        "color:#ffffff;padding:32px 24px 28px 24px;text-align:center;"
        "border-bottom:3px solid #3a3a5c;"
    ),
    "header_title": (
        "font-size:28px;font-weight:700;margin:0 0 4px 0;letter-spacing:1px;"
    ),
    "header_date": (
        "font-size:14px;opacity:0.85;margin:0;"
    ),
    "header_count": (
        "font-size:13px;opacity:0.75;margin:8px 0 0 0;"
    ),
    "lead_box": (
        "background-color:#f2f2f5;border-left:4px solid #1a1a2e;"
        "padding:16px 20px;margin:20px 24px;border-radius:0 8px 8px 0;"
        "font-size:14px;color:#333;line-height:1.7;"
    ),
    "section": (
        "padding:0 24px 16px 24px;"
    ),
    "section_title": (
        "font-size:18px;font-weight:700;color:#333;"
        "padding-bottom:8px;margin:20px 0 12px 0;"
        "border-bottom:2px solid #e0e0e0;"
    ),
    "item": (
        "padding:12px 0;border-bottom:1px solid #f0f0f0;"
    ),
    "item_number": (
        "display:inline-block;width:24px;height:24px;"
        "background-color:#1a1a2e;color:#fff;border-radius:50%;"
        "text-align:center;line-height:24px;font-size:12px;font-weight:700;"
        "margin-right:8px;vertical-align:middle;"
    ),
    "item_title": (
        "font-size:16px;font-weight:600;color:#1a1a1a;"
        "text-decoration:none;line-height:1.4;"
    ),
    "item_meta": (
        "font-size:12px;color:#999;margin:4px 0 6px 0;"
    ),
    "item_summary": (
        "font-size:14px;color:#555;line-height:1.6;margin:6px 0 0 0;"
    ),
    "flash_section": (
        "padding:0 24px 20px 24px;"
    ),
    "flash_title": (
        "font-size:14px;font-weight:700;color:#333;margin:8px 0 2px 0;"
    ),
    "flash_item": (
        "font-size:13px;color:#555;line-height:1.5;margin:4px 0;"
        "padding-left:12px;border-left:2px solid #888;"
    ),
    "footer": (
        "background-color:#fafafa;padding:20px 24px;text-align:center;"
        "font-size:12px;color:#999;line-height:1.8;"
    ),
    "footer_link": (
        "color:#1a1a2e;text-decoration:underline;"
    ),
}


def _style(styles: dict, extra: str = "") -> str:
    """合并样式字典为内联 style 字符串。"""
    base = ";".join(f"{k}:{v}" for k, v in styles.items())
    if extra:
        base = base + ";" + extra
    return base


# ---- HTML 片段 ----

def _h(text: Optional[str]) -> str:
    """HTML 转义。"""
    return html_mod.escape(str(text or ""), quote=False)


def _render_header(date: str, total: int, lead: str) -> str:
    parts = []
    parts.append('<div style="{}">'.format(STYLE["header"]))
    parts.append('<h1 style="{}">AI HOT 日报</h1>'.format(STYLE["header_title"]))
    if date:
        parts.append('<p style="{}">{}</p>'.format(STYLE["header_date"], _h(date)))
    parts.append('<p style="{}">共 {} 条</p>'.format(STYLE["header_count"], total))
    parts.append('</div>')
    return "\n".join(parts)


def _render_lead(lead: str) -> str:
    if not lead:
        return ""
    parts = []
    parts.append('<div style="{}">'.format(STYLE["lead_box"]))
    parts.append('<strong>📝 主编点评：</strong>{}'.format(_h(lead)))
    parts.append('</div>')
    return "\n".join(parts)


def _render_item(item: dict, num: int) -> str:
    parts = []
    parts.append('<div style="{}">'.format(STYLE["item"]))

    # 编号 + 标题（可点击）
    num_html = '<span style="{}">{}</span>'.format(STYLE["item_number"], num)
    title = _h(item.get("title", "无标题"))
    url = _h(item.get("url", ""))
    if url:
        title_html = '<a href="{}" style="{}" target="_blank">{}</a>'.format(
            url, STYLE["item_title"], title
        )
    else:
        title_html = '<span style="{}">{}</span>'.format(STYLE["item_title"], title)

    parts.append(f'<div>{num_html} {title_html}</div>')

    # 来源 + 时间
    source = _h(item.get("source", ""))
    time_str = _h(item.get("time_str", ""))
    meta_parts = []
    if source:
        meta_parts.append(source)
    if time_str:
        meta_parts.append(time_str)
    if meta_parts:
        parts.append(
            '<div style="{}">{}</div>'.format(
                STYLE["item_meta"], " · ".join(meta_parts)
            )
        )

    # 摘要
    summary = _h(item.get("summary", ""))
    if summary:
        parts.append(
            '<p style="{}">{}</p>'.format(STYLE["item_summary"], summary)
        )

    parts.append('</div>')
    return "\n".join(parts)


def _render_section(section: dict, start_num: int) -> tuple[str, int]:
    """渲染一个版块，返回 (html, 下一个编号)。"""
    label = section.get("label", "其他")
    items = section.get("items", [])
    if not items:
        return "", start_num

    parts = []
    parts.append('<div style="{}">'.format(STYLE["section"]))
    # 版块图标
    icons = {
        "模型发布/更新": "🧠",
        "产品发布/更新": "🚀",
        "行业动态": "📡",
        "论文研究": "📄",
        "技巧与观点": "💡",
        "其他": "📌",
    }
    icon = icons.get(label, "📌")
    parts.append(
        '<h2 style="{}">{} {}</h2>'.format(STYLE["section_title"], icon, _h(label))
    )

    num = start_num
    for item in items:
        parts.append(_render_item(item, num))
        num += 1

    parts.append('</div>')
    return "\n".join(parts), num


def _render_flashes(flashes: list[dict]) -> str:
    if not flashes:
        return ""
    parts = []
    parts.append('<div style="{}">'.format(STYLE["flash_section"]))
    parts.append(
        '<h2 style="{}">⚡ 快讯</h2>'.format(STYLE["section_title"])
    )
    for f in flashes:
        title = _h(f.get("title", ""))
        source = _h(f.get("source", ""))
        url = _h(f.get("url", ""))
        time_str = _h(f.get("time_str", ""))

        if url:
            title_html = '<a href="{}" style="color:#333;text-decoration:none;" target="_blank">{}</a>'.format(
                url, title
            )
        else:
            title_html = title

        meta = " · ".join(filter(None, [source, time_str]))
        parts.append('<div style="{}">'.format(STYLE["flash_item"]))
        parts.append(f'<div style="font-weight:600;">{title_html}</div>')
        if meta:
            parts.append(f'<div style="font-size:12px;color:#999;">{meta}</div>')
        parts.append('</div>')

    parts.append('</div>')
    return "\n".join(parts)


def _render_footer() -> str:
    parts = []
    parts.append('<div style="{}">'.format(STYLE["footer"]))
    parts.append(
        '数据来自 <a href="https://aihot.virxact.com" style="{}" target="_blank">'
        'aihot.virxact.com</a>'.format(STYLE["footer_link"])
    )
    parts.append('<br>')
    parts.append(
        '本邮件由 AI HOT Daily Bot 自动发送 · '
        '每天北京时间 09:00'
    )
    parts.append('</div>')
    return "\n".join(parts)


# ---- 主渲染入口 ----

def render_html(report: dict) -> str:
    """
    把归一化的 report dict 渲染为完整 HTML 邮件。

    Args:
        report: { date, lead, sections, flashes, total }

    Returns:
        完整 HTML 字符串。
    """
    date = report.get("date", "")
    total = report.get("total", 0)
    lead = report.get("lead", "")
    sections = report.get("sections", [])
    flashes = report.get("flashes", [])

    parts = []
    parts.append('<!DOCTYPE html>')
    parts.append('<html lang="zh-CN">')
    parts.append('<head>')
    parts.append('<meta charset="UTF-8">')
    parts.append(
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
    )
    parts.append(f"<title>AI HOT 日报 · {_h(date)}</title>")
    parts.append('</head>')
    parts.append(f'<body style="{STYLE["body"]}">')
    parts.append(f'<div style="{STYLE["container"]}">')

    # Header
    parts.append(_render_header(date, total, lead))

    # 主编点评
    if lead:
        parts.append(_render_lead(lead))

    # Sections
    num = 1
    for sec in sections:
        html_part, num = _render_section(sec, num)
        parts.append(html_part)

    # 快讯
    parts.append(_render_flashes(flashes))

    # Footer
    parts.append(_render_footer())

    parts.append('</div>')
    parts.append('</body>')
    parts.append('</html>')

    return "\n".join(parts)
