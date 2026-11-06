#!/usr/bin/env python3
"""查询工作记录

用法:
  python query.py --today                    # 查询今天
  python query.py --date 2026-08-17          # 查询某天
  python query.py --week                     # 查询本周
  python query.py --range 2026-08-11 2026-08-15  # 查询范围
"""

import argparse
import sqlite3
import json
from pathlib import Path
from datetime import datetime, date, timedelta

DB_PATH = Path(__file__).parent.parent / "work.db"


def query_logs(start_date, end_date):
    """查询指定日期范围的工作记录（包含status）"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        SELECT 
            wl.date,
            wl.time,
            p.name as project,
            wl.task,
            wl.content,
            wl.category,
            wl.duration_min,
            wl.status,
            wl.id
        FROM work_logs wl
        JOIN projects p ON wl.project_id = p.id
        WHERE wl.date >= ? AND wl.date <= ?
        ORDER BY wl.date, wl.time
    """, (start_date, end_date))
    
    rows = c.fetchall()
    conn.close()
    
    return rows


def format_output(rows, title):
    """格式化输出，区分已完成和计划中"""
    print(f"\n{title}\n")
    
    if not rows:
        print("暂无记录\n")
        return
    
    # 按日期分组
    by_date = {}
    for row in rows:
        log_date = row[0]
        if log_date not in by_date:
            by_date[log_date] = []
        by_date[log_date].append(row)
    
    for log_date in sorted(by_date.keys()):
        print(f"--- {log_date} ---")
        done_rows = [r for r in by_date[log_date] if r[7] == 'done']
        planned_rows = [r for r in by_date[log_date] if r[7] == 'planned']
        
        # 已完成
        if done_rows:
            print("✅ 已完成:")
            for row in done_rows:
                log_date, log_time, project, task, content, category, duration, status, rid = row
                if " " in str(log_time):
                    time_part = log_time.split(" ")[1][:5]
                    full_time = log_time
                else:
                    time_part = log_time[:5]
                    full_time = f"{log_date} {log_time}"
                duration_str = f"{duration}min" if duration else ""
                print(f"  {full_time}【{project}】{content} [{category}] {duration_str}")
        
        # 计划中
        if planned_rows:
            print("⏳ 计划中:")
            for row in planned_rows:
                log_date, log_time, project, task, content, category, duration, status, rid = row
                if " " in str(log_time):
                    time_part = log_time.split(" ")[1][:5]
                    full_time = log_time
                else:
                    time_part = log_time[:5]
                    full_time = f"{log_date} {log_time}"
                duration_str = f"{duration}min" if duration else ""
                print(f"  {full_time}【{project}】{content} [{category}] {duration_str}")
        
        # 当日合计（只算已完成的）
        done_total = sum(r[6] for r in done_rows if r[6])
        print(f"\n当日合计: {done_total}min ({done_total/60:.1f}h)\n")


def query_today():
    today = date.today().isoformat()
    rows = query_logs(today, today)
    format_output(rows, f"今日工作记录 ({today})")


def query_date(target_date):
    rows = query_logs(target_date, target_date)
    format_output(rows, f"工作记录 ({target_date})")


def query_week():
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    rows = query_logs(monday.isoformat(), sunday.isoformat())
    format_output(rows, f"本周工作记录 ({monday} ~ {sunday})")


def query_range(start, end):
    rows = query_logs(start, end)
    format_output(rows, f"工作记录 ({start} ~ {end})")


if __name__ == "__main__":
    # 输出当前系统时间（防止 AI 算错）
    now = datetime.now()
    weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    weekday = weekday_names[now.weekday()]
    print(f"当前系统时间: {now.strftime('%Y-%m-%d %H:%M:%S')} {weekday}\n")
    
    parser = argparse.ArgumentParser(description="查询工作记录")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--today", action="store_true", help="查询今天")
    group.add_argument("--date", help="查询某天 YYYY-MM-DD")
    group.add_argument("--week", action="store_true", help="查询本周")
    group.add_argument("--range", nargs=2, metavar=("START", "END"), help="查询范围")
    
    args = parser.parse_args()
    
    if args.today:
        query_today()
    elif args.date:
        query_date(args.date)
    elif args.week:
        query_week()
    elif args.range:
        query_range(args.range[0], args.range[1])
