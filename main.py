#!/usr/bin/env python3
"""
AI HOT 每日邮件日报 — 主入口。

用法:
    python main.py          # 发送今日日报
    python main.py --dry    # 只打印 HTML，不发送

环境变量（.env / GitHub Secrets）:
    SMTP_HOST      SMTP 服务器地址（必填）
    SMTP_PORT      SMTP 端口（默认 587）
    SMTP_USER      发件人账号（必填）
    SMTP_PASS      发件人密码（必填）
    TO_EMAIL       收件人邮箱（必填）
    FROM_EMAIL     发件人显示邮箱（可选，默认同 SMTP_USER）
"""

import argparse
import logging
import sys

# 本地调试：自动加载 .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src.fetch_report import fetch_report
from src.render_email import render_html
from src.send_email import send_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")


def main() -> None:
    parser = argparse.ArgumentParser(description="AI HOT 每日邮件日报")
    parser.add_argument(
        "--dry",
        action="store_true",
        help="只生成 HTML 并打印到 stdout，不发送邮件",
    )
    args = parser.parse_args()

    # 1. 拉数据
    logger.info("📡 拉取 AI HOT 数据...")
    try:
        report = fetch_report()
    except Exception as e:
        logger.error("拉取数据失败: %s", e)
        sys.exit(1)

    total = report.get("total", 0)
    date_str = report.get("date", "?")
    logger.info("获取到 %s 的日报，共 %d 条", date_str, total)

    if total == 0:
        logger.warning("今日无数据，跳过发送。")
        sys.exit(0)

    # 2. 渲染 HTML
    logger.info("🎨 渲染 HTML 邮件...")
    html_content = render_html(report)

    # 3. 发送
    subject = f"AI HOT 日报 · {date_str}"
    if args.dry:
        # Windows 控制台可能不支持 emoji → 写文件最稳妥
        out_path = "preview.html"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info("Dry run 完成，HTML 已写入 %s，未发送邮件。", out_path)
    else:
        logger.info("📧 发送邮件...")
        try:
            send_email(html_content, subject=subject)
            logger.info("✅ 邮件已发送！")
        except Exception as e:
            logger.error("发送邮件失败: %s", e)
            sys.exit(1)


if __name__ == "__main__":
    main()
