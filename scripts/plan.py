#!/usr/bin/env python3
"""管理周计划

用法:
  python plan.py --add --items '[{"text":"PRD编写","project":"渔船审图"}]'  # 添加本周计划
  python plan.py --show                                                    # 显示本周计划
  python plan.py --update --index 1 --status done                          # 更新计划项状态
  python plan.py --progress                                                # 显示进度
"""

import argparse
import sqlite3
import json
from pathlib import Path
from datetime import date, timedelta

DB_PATH = Path(__file__).parent.parent / "work.db"


def get_week_range(target_date=None):
    """获取指定日期所在周的周一和周日"""
    if not target_date:
        target_date = date.today()
    monday = target_date - timedelta(days=target_date.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def get_or_create_week_plan(conn):
    """获取或创建本周计划"""
    monday, sunday = get_week_range()
    
    c = conn.cursor()
    c.execute(
        "SELECT id, plan_items FROM weekly_plans WHERE week_start = ? AND week_end = ?",
        (monday.isoformat(), sunday.isoformat())
    )
    row = c.fetchone()
    
    if row:
        return row[0], json.loads(row[1])
    
    # 创建新计划
    c.execute(
        "INSERT INTO weekly_plans (week_start, week_end, plan_items) VALUES (?, ?, ?)",
        (monday.isoformat(), sunday.isoformat(), json.dumps([]))
    )
    conn.commit()
    return c.lastrowid, []


def add_plan(items_json):
    """添加周计划"""
    conn = sqlite3.connect(DB_PATH)
    plan_id, existing_items = get_or_create_week_plan(conn)
    
    new_items = json.loads(items_json)
    all_items = existing_items + new_items
    
    # 更新计划
    c = conn.cursor()
    c.execute(
        "UPDATE weekly_plans SET plan_items = ? WHERE id = ?",
        (json.dumps(all_items, ensure_ascii=False), plan_id)
    )
    
    # 创建进度记录
    for i, item in enumerate(new_items):
        index = len(existing_items) + i
        c.execute(
            "INSERT INTO plan_progress (plan_id, item_index, status) VALUES (?, ?, ?)",
            (plan_id, index, "pending")
        )
    
    conn.commit()
    conn.close()
    
    print(f"✅ 已添加 {len(new_items)} 项计划")
    show_plan()


def show_plan():
    """显示本周计划"""
    monday, sunday = get_week_range()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT id, plan_items FROM weekly_plans WHERE week_start = ? AND week_end = ?",
        (monday.isoformat(), sunday.isoformat())
    )
    row = c.fetchone()
    
    if not row:
        print("本周暂无计划")
        conn.close()
        return
    
    plan_id, items_json = row
    items = json.loads(items_json)
    
    # 获取进度
    c.execute(
        "SELECT item_index, status FROM plan_progress WHERE plan_id = ?",
        (plan_id,)
    )
    progress = {idx: status for idx, status in c.fetchall()}
    conn.close()
    
    print(f"\n📋 本周计划 ({monday} ~ {sunday})\n")
    
    done_count = sum(1 for s in progress.values() if s == "done")
    total = len(items)
    print(f"完成 {done_count}/{total}\n")
    
    for i, item in enumerate(items):
        status = progress.get(i, "pending")
        icon = "✅" if status == "done" else "⬜"
        text = item.get("text", "")
        project = item.get("project", "")
        project_str = f"【{project}】" if project else ""
        print(f"{icon} {i+1}. {project_str}{text}")
    
    print()


def update_progress(index, status):
    """更新计划项状态"""
    monday, sunday = get_week_range()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT id FROM weekly_plans WHERE week_start = ? AND week_end = ?",
        (monday.isoformat(), sunday.isoformat())
    )
    row = c.fetchone()
    
    if not row:
        print("本周暂无计划")
        conn.close()
        return
    
    plan_id = row[0]
    
    completed_at = date.today().isoformat() if status == "done" else None
    c.execute("""
        UPDATE plan_progress 
        SET status = ?, completed_at = ?
        WHERE plan_id = ? AND item_index = ?
    """, (status, completed_at, plan_id, index))
    
    conn.commit()
    conn.close()
    
    print(f"✅ 已更新计划项 {index+1} 状态为 {status}")
    show_plan()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="管理周计划")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--add", action="store_true", help="添加计划")
    group.add_argument("--show", action="store_true", help="显示计划")
    group.add_argument("--update", action="store_true", help="更新状态")
    group.add_argument("--progress", action="store_true", help="显示进度")
    
    parser.add_argument("--items", help="计划项JSON")
    parser.add_argument("--index", type=int, help="计划项序号(0开始)")
    parser.add_argument("--status", choices=["pending", "in_progress", "done"], help="状态")
    
    args = parser.parse_args()
    
    if args.add:
        add_plan(args.items)
    elif args.show or args.progress:
        show_plan()
    elif args.update:
        update_progress(args.index, args.status)
