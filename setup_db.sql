CREATE DATABASE IF NOT EXISTS aihot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE aihot;

CREATE TABLE IF NOT EXISTS daily_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report_date DATE NOT NULL UNIQUE COMMENT '日报日期',
    lead_text TEXT COMMENT '主编点评',
    total_items INT DEFAULT 0 COMMENT '条目总数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) COMMENT '日报记录';

CREATE TABLE IF NOT EXISTS report_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report_date DATE NOT NULL COMMENT '所属日报日期',
    section VARCHAR(50) NOT NULL COMMENT '所属版块',
    title VARCHAR(500) NOT NULL COMMENT '标题',
    summary TEXT COMMENT '摘要',
    source VARCHAR(200) COMMENT '来源',
    url VARCHAR(1000) COMMENT '原文链接',
    sort_order INT DEFAULT 0 COMMENT '排序',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_date (report_date),
    INDEX idx_section (section)
) COMMENT '日报条目';

CREATE TABLE IF NOT EXISTS report_flashes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report_date DATE NOT NULL COMMENT '所属日报日期',
    title VARCHAR(500) NOT NULL COMMENT '标题',
    source VARCHAR(200) COMMENT '来源',
    url VARCHAR(1000) COMMENT '链接',
    time_str VARCHAR(50) COMMENT '发布时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_date (report_date)
) COMMENT '快讯';

SHOW TABLES;
