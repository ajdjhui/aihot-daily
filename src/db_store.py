"""
MySQL 数据库存储模块。

把 fetch_report() 的归一化结果存入本地 MySQL 的 aihot 库。
按 report_date 去重：同一天重复跑不会重复插入。
"""

import logging
import os
from typing import Optional

import mysql.connector
from mysql.connector import Error

logger = logging.getLogger(__name__)

# 默认值：本地 MySQL
DEFAULTS = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "database": "aihot",
}


def _get_config() -> dict:
    """从环境变量读取数据库配置，未设置则用本地默认值。"""
    return {
        "host": os.getenv("DB_HOST", DEFAULTS["host"]),
        "port": int(os.getenv("DB_PORT", str(DEFAULTS["port"]))),
        "user": os.getenv("DB_USER", DEFAULTS["user"]),
        "password": os.getenv("DB_PASS", ""),
        "database": os.getenv("DB_NAME", DEFAULTS["database"]),
    }


def _connect(cfg: dict) -> Optional[mysql.connector.MySQLConnection]:
    """建立数据库连接。失败返回 None（不阻塞邮件发送）。"""
    try:
        conn = mysql.connector.connect(
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password=cfg["password"],
            database=cfg["database"],
            charset="utf8mb4",
            autocommit=False,
        )
        return conn
    except Error as e:
        logger.warning("数据库连接失败（跳过存库）: %s", e)
        return None


def save_report(report: dict) -> bool:
    """
    将日报存到 MySQL。

    去重策略：按 report_date 唯一，同一天重复调用会先删旧数据再写入，
    保证和最新一次拉取结果一致。

    Args:
        report: fetch_report() 返回的归一化 dict。

    Returns:
        True 表示写入成功，False 表示数据库不可用（跳过）。
    """
    cfg = _get_config()
    conn = _connect(cfg)
    if conn is None:
        return False

    date_str = report.get("date", "")
    lead = report.get("lead", "")
    sections = report.get("sections", [])
    flashes = report.get("flashes", [])
    total = report.get("total", 0)

    try:
        cursor = conn.cursor()

        # ---- 日报主表 ----
        cursor.execute(
            "INSERT INTO daily_reports (report_date, lead_text, total_items) "
            "VALUES (%s, %s, %s) "
            "ON DUPLICATE KEY UPDATE lead_text = VALUES(lead_text), total_items = VALUES(total_items)",
            (date_str, lead, total),
        )

        # ---- 条目明细：先删旧，再批量插入 ----
        cursor.execute("DELETE FROM report_items WHERE report_date = %s", (date_str,))

        order = 0
        for sec in sections:
            label = sec.get("label", "其他")
            for item in sec.get("items", []):
                order += 1
                cursor.execute(
                    "INSERT INTO report_items (report_date, section, title, summary, source, url, sort_order) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (
                        date_str,
                        label,
                        item.get("title", ""),
                        item.get("summary", ""),
                        item.get("source", ""),
                        item.get("url", ""),
                        order,
                    ),
                )

        # ---- 快讯：先删旧，再插入 ----
        cursor.execute("DELETE FROM report_flashes WHERE report_date = %s", (date_str,))

        for f in flashes:
            cursor.execute(
                "INSERT INTO report_flashes (report_date, title, source, url, time_str) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    date_str,
                    f.get("title", ""),
                    f.get("source", ""),
                    f.get("url", ""),
                    f.get("time_str", ""),
                ),
            )

        conn.commit()
        logger.info("✅ 数据已存入 MySQL: %s (%d 条)", date_str, total)
        return True

    except Error as e:
        conn.rollback()
        logger.warning("数据库写入失败: %s", e)
        return False
    finally:
        cursor.close()
        conn.close()
