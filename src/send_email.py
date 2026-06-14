"""
SMTP 邮件发送模块。

配置从环境变量读取（GitHub Actions 中用 Secrets，本地用 .env）。
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)

# 环境变量名
ENV_SMTP_HOST = "SMTP_HOST"
ENV_SMTP_PORT = "SMTP_PORT"
ENV_SMTP_USER = "SMTP_USER"
ENV_SMTP_PASS = "SMTP_PASS"
ENV_FROM_EMAIL = "FROM_EMAIL"
ENV_TO_EMAIL = "TO_EMAIL"

DEFAULT_SMTP_PORT = 587


def _get_config() -> dict:
    """从环境变量读取 SMTP 配置，缺失必填项时抛出明确错误。"""
    required = [ENV_SMTP_HOST, ENV_SMTP_USER, ENV_SMTP_PASS, ENV_TO_EMAIL]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise RuntimeError(
            f"缺少必需的 SMTP 环境变量: {', '.join(missing)}。"
            f"请在 .env 文件或 GitHub Secrets 中设置。"
        )

    port_str = os.getenv(ENV_SMTP_PORT, str(DEFAULT_SMTP_PORT))
    try:
        port = int(port_str)
    except ValueError:
        raise RuntimeError(f"{ENV_SMTP_PORT} 必须是整数，当前值: {port_str}")

    return {
        "host":       os.getenv(ENV_SMTP_HOST, ""),
        "port":       port,
        "user":       os.getenv(ENV_SMTP_USER, ""),
        "password":   os.getenv(ENV_SMTP_PASS, ""),
        "from_email": os.getenv(ENV_FROM_EMAIL) or os.getenv(ENV_SMTP_USER, ""),
        "to_email":   os.getenv(ENV_TO_EMAIL, ""),
    }


def send_email(
    html_content: str,
    subject: Optional[str] = None,
) -> None:
    """
    发送 HTML 邮件。

    Args:
        html_content: HTML 邮件正文。
        subject: 邮件主题，默认 "AI HOT 日报 · YYYY-MM-DD"。
    """
    cfg = _get_config()

    msg = MIMEMultipart("alternative")
    msg["From"] = cfg["from_email"]
    msg["To"] = cfg["to_email"]
    msg["Subject"] = subject or "AI HOT 日报"

    msg.attach(MIMEText(html_content, "html", "utf-8"))

    logger.info(
        "Connecting to SMTP %s:%d as %s ...",
        cfg["host"], cfg["port"], cfg["user"],
    )
    try:
        if cfg["port"] == 465:
            # SSL
            server = smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=30)
        else:
            # STARTTLS
            server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=30)
            server.ehlo()
            if server.has_extn("STARTTLS"):
                server.starttls()
                server.ehlo()

        server.login(cfg["user"], cfg["password"])
        server.sendmail(cfg["from_email"], cfg["to_email"], msg.as_string())
        server.quit()
    except smtplib.SMTPAuthenticationError:
        raise RuntimeError(
            "SMTP 认证失败，请检查 SMTP_USER / SMTP_PASS 是否正确。"
            "如果是 Gmail，需要用「应用专用密码」而非登录密码。"
        )
    except smtplib.SMTPConnectError:
        raise RuntimeError(
            f"无法连接到 SMTP 服务器 {cfg['host']}:{cfg['port']}，"
            f"请检查 SMTP_HOST / SMTP_PORT。"
        )

    logger.info("Email sent to %s", cfg["to_email"])
