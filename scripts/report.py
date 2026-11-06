#!/usr/bin/env python3
"""生成周报

用法: python report.py --week [YYYY-Www] [--output markdown|text]

输出周报内容（Markdown格式），供Agent发送到飞书文档
"""

import argparse
import sqlite3
import json
from pathlib import Path
from datetime import date, timedelta, datetime

DB_PATH = Path(__file__).parent.parent / "work.db"


def get_week_range(week_str=None):
    """获取周范围
    
    week_str: "2026-W34" 或 None(当前周)
    """
    if not week_str:
        today = date.today()
        monday = today - timedelta(days=today.weekday())
    else:
        # 解析 "2026-W34"，用 ISO 标准周精确计算周一
        year, week = week_str.split("-W")
        monday = date.fromisocalendar(int(year), int(week), 1)
    
    sunday = monday + timedelta(days=6)
    return monday, sunday


def generate_report(week_str=None):
    """生成周报"""
    monday, sunday = get_week_range(week_str)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 获取本周计划
    c.execute(
        "SELECT id, plan_items FROM weekly_plans WHERE week_start = ? AND week_end = ?",
        (monday.isoformat(), sunday.isoformat())
    )
    plan_row = c.fetchone()
    
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
    
    # 获取计划进度
    if plan_row:
        plan_id, items_json = plan_row
        plan_items = json.loads(items_json)
        
        c.execute(
            "SELECT item_index, status, completed_at FROM plan_progress WHERE plan_id = ?",
            (plan_id,)
        )
        progress_rows = c.fetchall()
        progress = {idx: (status, completed_at) for idx, status, completed_at in progress_rows}
    else:
        plan_items = []
        progress = {}
    
    conn.close()
    
    # 计算周数
    week_num = monday.isocalendar()[1]
    year = monday.year
    
    # 生成Markdown
    output = []
    output.append(f"# 甘来杰｜{year}-W{week_num:02d} 周报\n")
    
    # 本周进展
    output.append("## 本周进展\n")
    
    # 按项目分组已完成的工作
    project_work = {}
    for log_date, log_time, project, task, content, category, duration in logs:
        if project not in project_work:
            project_work[project] = []
        project_work[project].append({
            "date": log_date,
            "time": log_time,
            "task": task,
            "content": content,
            "category": category,
            "duration": duration
        })
    
    # 输出每个项目的进展
    item_num = 1
    for project, works in project_work.items():
        for work in works:
            task_str = work["task"] if work["task"] else work["content"]
            output.append(f"{item_num}. 【{project}】{task_str}")
            item_num += 1
    
    if not project_work:
        output.append("（本周暂无工作记录）")
    
    output.append("")
    
    # 本周未完成
    output.append("## 本周未完成\n")
    
    has_incomplete = False
    if plan_items:
        for i, item in enumerate(plan_items):
            status = progress.get(i, ("pending", None))[0]
            if status != "done":
                project = item.get("project", "")
                text = item.get("text", "")
                project_str = f"【{project}】" if project else ""
                output.append(f"1. {project_str}{text}")
                has_incomplete = True
    
    if not has_incomplete:
        output.append("无")
    
    output.append("")
    
    # 下周计划
    output.append("## 下周计划\n")
    output.append("（由Agent根据本周未完成项和上下文生成）")
    output.append("")
    
    # 待协调工作
    output.append("## 待协调工作\n")
    output.append("（由Agent根据工作内容提取）")
    output.append("")
    
    # 工作建议
    output.append("## 工作建议\n")
    output.append("（由Agent根据工作内容提取）")
    
    return "\n".join(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="生成周报")
    parser.add_argument("--week", help="周数 YYYY-Www")
    parser.add_argument("--output", choices=["markdown", "text"], default="markdown")
    
    args = parser.parse_args()
    
    report = generate_report(args.week)
    print(report)
