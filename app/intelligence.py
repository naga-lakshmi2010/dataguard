import pandas as pd
from app.database import get_connection

def calculate_health_score():
    conn = get_connection()
    runs = pd.read_sql_query("SELECT * FROM pipeline_runs", conn)
    recoveries = pd.read_sql_query("SELECT * FROM recovery_logs WHERE outcome = 'SUCCESS'", conn)
    conn.close()

    if runs.empty:
        return 100.0

    total_runs = len(runs)
    clean_runs = len(runs[runs["status"] == "SUCCESS"])
    failed_runs = len(runs[runs["status"] == "FAILED"])
    recovered_runs = len(recoveries)

    if failed_runs == 0:
        return 100.0

    recovery_ratio = min(recovered_runs / failed_runs, 1.0)
    score = ((0.6 * (clean_runs / total_runs)) + (0.4 * recovery_ratio)) * 100
    return round(score, 1)

def get_recurring_insights():
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT failure_type, COUNT(*) as occurrences
        FROM issues
        GROUP BY failure_type
        HAVING occurrences >= 2
        ORDER BY occurrences DESC
    """, conn)
    conn.close()
    return df

def get_kb_recommendation(failure_type: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT recommended_solution, times_resolved FROM knowledge_base WHERE failure_type = ?", (failure_type,))
    row = cur.fetchone()
    conn.close()
    if row:
        return f"{row[0]} (Previously resolved {row[1]} times)"
    return "Inspect raw CSV file and escalate to Data Engineering lead."

def build_team_notification(filename: str, issues: list):
    """Generates one consolidated team alert instead of spamming individual errors."""
    severities = [i["severity"] for i in issues]
    highest_sev = "CRITICAL" if "CRITICAL" in severities else ("HIGH" if "HIGH" in severities else "MEDIUM")
    summary_lines = "\n".join([f"- [{i['failure_type']}] {i['root_cause']}" for i in issues])
    return {
        "channel": "#data-pipeline-alerts (Data Engineering Team)",
        "severity": highest_sev,
        "subject": f"DataGuard Alert: {len(issues)} issue(s) detected in '{filename}'",
        "body": summary_lines
    }