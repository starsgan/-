#!/usr/bin/env python3
"""记录工作内容 — 解析输入并存入DB

用法: python record.py --project "渔船审图" --content "PRD功能清单" --category "文档" --duration 150 [--task "PRD编写"] [--date "2026-08-17"] [--time "09:10:32"]
"""

import argparse
import sqlite3
import json
import sys
from pathlib import Path
from datetime import datetime, date

DB_PATH = Path(__file__).parent.parent / "work.db"


def get_or_create_project(conn, name, category=None):
    """获取或创建项目"""
    c = conn.cursor()
    c.execute("SELECT id FROM projects WHERE name = ?", (name,))
    row = c.fetchone()
    if row:
        return row[0]
    
    c.execute(
        "INSERT INTO projects (name, category) VALUES (?, ?)",
        (name, category or "其他")
    )
    conn.commit()
    return c.lastrowid


def get_current_week_plan(conn):
    """获取当前周的计划ID"""
    today = date.today()
    # 计算本周一
    monday = today - __import__('datetime').timedelta(days=today.weekday())
    sunday = monday + __import__('datetime').timedelta(days=6)
    
    c = conn.cursor()
    c.execute(
        "SELECT id FROM weekly_plans WHERE week_start = ? AND week_end = ?",
        (monday.isoformat(), sunday.isoformat())
    )
    row = c.fetchone()
    return row[0] if row else None


def record_work(project_name, content, category, duration_min, 
                task=None, log_date=None, log_time=None, status='done'):
    """记录一条工作"""
    conn = sqlite3.connect(DB_PATH)
    
    # 获取/创建项目
    project_id = get_or_create_project(conn, project_name)
    
    # 默认时间
    now = datetime.now()
    if not log_date:
        log_date = now.strftime("%Y-%m-%d")
    if not log_time:
        log_time = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # 获取当前周计划
    week_id = get_current_week_plan(conn)
    
    # 插入记录
    c = conn.cursor()
    c.execute("""
        INSERT INTO work_logs (date, time, project_id, task, content, category, duration_min, week_id, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (log_date, log_time, project_id, task, content, category, duration_min, week_id, status))
    conn.commit()
    
    record_id = c.lastrowid
    conn.close()
    
    # 输出确认
    timestamp = log_time if " " in log_time else f"{log_date} {log_time}"
    status_icon = "⏳" if status == 'planned' else "✅"
    print(f"{status_icon} 已记录 [{record_id}] ({status})")
    print(f"{timestamp}【{project_name}】{content} [{category}] {duration_min}min")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="记录工作内容")
    parser.add_argument("--project", required=True, help="项目名称")
    parser.add_argument("--content", required=True, help="工作内容")
    parser.add_argument("--category", default="其他", help="分类")
    parser.add_argument("--duration", type=int, default=0, help="工时(分钟)")
    parser.add_argument("--task", help="所属任务")
    parser.add_argument("--date", help="日期 YYYY-MM-DD")
    parser.add_argument("--time", help="时间 YYYY-MM-DD HH:MM:SS")
    parser.add_argument("--status", default="done", choices=["done", "planned"], help="状态: done=已完成, planned=计划中")
    
    args = parser.parse_args()
    record_work(args.project, args.content, args.category, args.duration,
                args.task, args.date, args.time, args.status)
