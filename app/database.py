import sqlite3
from datetime import datetime

DB_PATH = "dataguard.db"

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # 1. Pipeline Runs (Execution History & Comparison)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            filename TEXT,
            total_rows INTEGER,
            valid_rows INTEGER,
            invalid_rows INTEGER,
            processing_time_ms REAL,
            status TEXT
        )
    """)

    # 2. Centralized Issue Tracking & Team Assignment
    cur.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            failure_type TEXT,
            severity TEXT,
            root_cause TEXT,
            assigned_to TEXT DEFAULT 'Unassigned',
            priority TEXT DEFAULT 'Medium',
            notes TEXT DEFAULT '',
            status TEXT DEFAULT 'Open',
            created_at TEXT
        )
    """)

    # 3. Recovery History & Admin Approval Workflow
    cur.execute("""
        CREATE TABLE IF NOT EXISTS recovery_logs (
            recovery_id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_id INTEGER,
            method TEXT,
            approval_status TEXT,
            approved_by TEXT,
            retry_count INTEGER DEFAULT 1,
            outcome TEXT,
            timestamp TEXT
        )
    """)

    # 4. DataGuard Knowledge Base
    cur.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_base (
            kb_id INTEGER PRIMARY KEY AUTOINCREMENT,
            failure_type TEXT UNIQUE,
            recommended_solution TEXT,
            times_resolved INTEGER DEFAULT 1
        )
    """)

    # Pre-seed Knowledge Base with initial solutions
    seed_kb = [
        ("Missing Column", "Verify upstream CSV export schema and ensure all required columns (Order ID, Product, Quantity, Price, Order Date) are mapped.", 3),
        ("Duplicate Records", "Run automated deduplication on 'Order ID' keeping the first valid entry.", 5),
        ("Invalid Values", "Filter out rows with negative Quantity or zero/negative Price before aggregation.", 4),
        ("Missing Values", "Drop incomplete records or impute missing numeric fields after admin review.", 2),
        ("Invalid Date Format", "Standardize 'Order Date' to YYYY-MM-DD format.", 2),
    ]
    for f_type, sol, count in seed_kb:
        cur.execute("""
            INSERT OR IGNORE INTO knowledge_base (failure_type, recommended_solution, times_resolved)
            VALUES (?, ?, ?)
        """, (f_type, sol, count))

    conn.commit()
    conn.close()

def log_run(filename, total_rows, valid_rows, invalid_rows, proc_time_ms, status):
    conn = get_connection()
    cur = conn.cursor()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        INSERT INTO pipeline_runs (timestamp, filename, total_rows, valid_rows, invalid_rows, processing_time_ms, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (ts, filename, total_rows, valid_rows, invalid_rows, proc_time_ms, status))
    run_id = cur.lastrowid
    conn.commit()
    conn.close()
    return run_id

def log_issue(run_id, failure_type, severity, root_cause):
    conn = get_connection()
    cur = conn.cursor()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        INSERT INTO issues (run_id, failure_type, severity, root_cause, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (run_id, failure_type, severity, root_cause, ts))
    issue_id = cur.lastrowid
    conn.commit()
    conn.close()
    return issue_id