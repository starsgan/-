#!/usr/bin/env python3
"""生成工时清单

用法: python timesheet.py [--week YYYY-Www]

输出工时清单（Markdown格式），供Agent发送到飞书文档
"""

import argparse
import sqlite3
import json
from pathlib import Path
from datetime import date, timedelta

DB_PATH = Path(__file__).parent.parent / "work.db"


def get_week_range(week_str=None):
    """获取周范围"""
    if not week_str:
        today = date.today()
        monday = today - timedelta(days=today.weekday())
    else:
        # 解析 "2026-W34"，用 ISO 标准周精确计算周一
        year, week = week_str.split("-W")
        monday = date.fromisocalendar(int(year), int(week), 1)
    
    sunday = monday + timedelta(days=6)
    return monday, sunday


def generate_timesheet(week_str=None):
    """生成工时清单"""
    monday, sunday = get_week_range(week_str)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 获取本周工作记录
    c.execute("""
        SELECT 
            wl.date,
            wl.time,
            p.name as project,
            wl.task,
            wl.content,
            wl.category,
            wl.duration_min
        FROM work_logs wl
        JOIN projects p ON wl.project_id = p.id
        WHERE wl.date >= ? AND wl.date <= ?
        ORDER BY wl.date, wl.time
    """, (monday.isoformat(), sunday.isoformat()))
    
    logs = c.fetchall()
    conn.close()
    
    # 计算周数
    week_num = monday.isocalendar()[1]
    year = monday.year
    
    # 生成Markdown
    output = []
    output.append(f"# 工时清单 - {year}年第{week_num}周（{monday.strftime('%m/%d')} ~ {sunday.strftime('%m/%d')}）\n")
    
    # 明细表
    output.append("## 明细\n")
    output.append("| # | 日期 | 时间 | 项目 | 所属任务 | 工作内容 | 类别 | 工时 |")
    output.append("|---|------|------|------|----------|----------|------|------|")
    
    total_min = 0
    for i, (log_date, log_time, project, task, content, category, duration) in enumerate(logs, 1):
        time_part = log_time.split(" ")[1][:5] if " " in log_time else log_time[:5]
        duration_str = f"{duration}min" if duration else "-"
        task_str = task if task else "-"
        
        output.append(f"| {i} | {log_date} | {time_part} | {project} | {task_str} | {content} | {category} | {duration_str} |")
        
        if duration:
            total_min += duration
    
    output.append("")
    
    # 汇总
    output.append("## 汇总\n")
    
    # 按项目汇总
    output.append("### 按项目\n")
    output.append("| 项目 | 工时 |")
    output.append("|------|------|")
    
    project_totals = {}
    for log_date, log_time, project, task, content, category, duration in logs:
        if duration:
            project_totals[project] = project_totals.get(project, 0) + duration
    
    for project, total in project_totals.items():
        output.append(f"| {project} | {total}min ({total/60:.1f}h) |")
    
    output.append(f"| **合计** | **{total_min}min ({total_min/60:.1f}h)** |")
    output.append("")
    
    # 按类别汇总
    output.append("### 按类别\n")
    output.append("| 类别 | 工时 |")
    output.append("|------|------|")
    
    category_totals = {}
    for log_date, log_time, project, task, content, category, duration in logs:
        if duration:
            category_totals[category] = category_totals.get(category, 0) + duration
    
    for category, total in sorted(category_totals.items(), key=lambda x: -x[1]):
        output.append(f"| {category} | {total}min ({total/60:.1f}h) |")
    
    output.append(f"| **合计** | **{total_min}min ({total_min/60:.1f}h)** |")
    output.append("")
    
    # 按天汇总
    output.append("### 按天\n")
    output.append("| 日期 | 工时 |")
    output.append("|------|------|")
    
    day_totals = {}
    for log_date, log_time, project, task, content, category, duration in logs:
        if duration:
            day_totals[log_date] = day_totals.get(log_date, 0) + duration
    
    for day, total in sorted(day_totals.items()):
        weekday = date.fromisoformat(day).strftime("%A")
        weekday_cn = {"Monday": "周一", "Tuesday": "周二", "Wednesday": "周三", 
                       "Thursday": "周四", "Friday": "周五", "Saturday": "周六", 
                       "Sunday": "周日"}[weekday]
        output.append(f"| {day}（{weekday_cn}） | {total}min ({total/60:.1f}h) |")
    
    output.append(f"| **合计** | **{total_min}min ({total_min/60:.1f}h)** |")
    
    return "\n".join(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="生成工时清单")
    parser.add_argument("--week", help="周数 YYYY-Www")
    
    args = parser.parse_args()
    
    timesheet = generate_timesheet(args.week)
    print(timesheet)
