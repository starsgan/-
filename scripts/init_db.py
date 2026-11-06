#!/usr/bin/env python3
"""初始化 work-tracker 数据库"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "work.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 项目表
    c.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        category TEXT DEFAULT '其他',
        status TEXT DEFAULT 'active',
        description TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 周计划表
    c.execute("""
    CREATE TABLE IF NOT EXISTS weekly_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        week_start DATE NOT NULL,
        week_end DATE NOT NULL,
        plan_items TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 计划进度表
    c.execute("""
    CREATE TABLE IF NOT EXISTS plan_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id INTEGER NOT NULL,
        item_index INTEGER NOT NULL,
        status TEXT DEFAULT 'pending',
        completed_at DATETIME,
        note TEXT,
        FOREIGN KEY (plan_id) REFERENCES weekly_plans(id)
    )
    """)
    
    # 工作记录表
    c.execute("""
    CREATE TABLE IF NOT EXISTS work_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATE NOT NULL,
        time DATETIME NOT NULL,
        project_id INTEGER NOT NULL,
        task TEXT,
        content TEXT NOT NULL,
        category TEXT DEFAULT '其他',
        duration_min INTEGER,
        week_id INTEGER,
        FOREIGN KEY (project_id) REFERENCES projects(id),
        FOREIGN KEY (week_id) REFERENCES weekly_plans(id)
    )
    """)
    
    conn.commit()
    conn.close()
    print(f"数据库初始化完成: {DB_PATH}")

if __name__ == "__main__":
    init_db()
