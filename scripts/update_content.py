#!/usr/bin/env python3
"""更新工作记录的content字段

用法: python update_content.py --id 1 --content "调研船舶管理部海务、机务、保障等业务场景，输出需求分析报告"
"""

import argparse
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "work.db"


def update_content(record_id, new_content):
    """更新指定记录的content"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE work_logs SET content = ? WHERE id = ?", (new_content, record_id))
    conn.commit()
    conn.close()
    print(f"✅ 已更新记录 [{record_id}] 的内容")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="更新工作内容")
    parser.add_argument("--id", type=int, required=True, help="记录ID")
    parser.add_argument("--content", required=True, help="新的工作内容")
    
    args = parser.parse_args()
    update_content(args.id, args.content)
