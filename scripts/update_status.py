#!/usr/bin/env python3
"""更新工作记录状态（planned -> done）

用法: python update_status.py --id 1 --status done
"""

import argparse
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "work.db"


def update_status(record_id, new_status):
    """更新指定记录的状态"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if new_status == 'done':
        c.execute("UPDATE work_logs SET status = ?, time = ? WHERE id = ?", 
                  (new_status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), record_id))
    else:
        c.execute("UPDATE work_logs SET status = ? WHERE id = ?", 
                  (new_status, record_id))
    
    conn.commit()
    conn.close()
    print(f"✅ 已更新记录 [{record_id}] 状态为 {new_status}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="更新工作状态")
    parser.add_argument("--id", type=int, required=True, help="记录ID")
    parser.add_argument("--status", required=True, choices=["done", "planned"], help="状态")
    
    args = parser.parse_args()
    update_status(args.id, args.status)
