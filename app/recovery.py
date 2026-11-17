import pandas as pd
from datetime import datetime
from app.database import get_connection

def execute_recovery(df: pd.DataFrame, issue_ids: list, approved_by: str, approval_status: str):
    """
    Dynamically cleans duplicates, missing values, negative numbers, and date columns for any CSV.
    """
    cleaned_df = df.copy()
    actions_taken = []

    # 1. Remove duplicates
    before_dup = len(cleaned_df)
    if "Order ID" in cleaned_df.columns:
        cleaned_df = cleaned_df.drop_duplicates(subset=["Order ID"], keep="first")
    else:
        cleaned_df = cleaned_df.drop_duplicates(keep="first")
    if len(cleaned_df) < before_dup:
        actions_taken.append(f"Removed {before_dup - len(cleaned_df)} duplicate row(s)")

    # 2. Drop rows with missing values
    before_null = len(cleaned_df)
    cleaned_df = cleaned_df.dropna()
    if len(cleaned_df) < before_null:
        actions_taken.append(f"Dropped {before_null - len(cleaned_df)} row(s) with missing values")

    # 3. Filter out negative values across all numeric columns
    numeric_cols = cleaned_df.select_dtypes(include=["number"]).columns
    for col in numeric_cols:
        before_neg = len(cleaned_df)
        cleaned_df = cleaned_df[cleaned_df[col] >= 0]
        if len(cleaned_df) < before_neg:
            actions_taken.append(f"Removed {before_neg - len(cleaned_df)} row(s) with negative '{col}'")

    # 4. Standardize any date columns
    date_cols = [col for col in cleaned_df.columns if "date" in col.lower()]
    for col in date_cols:
        cleaned_df[col] = pd.to_datetime(cleaned_df[col], errors="coerce").dt.strftime("%Y-%m-%d")
        cleaned_df = cleaned_df.dropna(subset=[col])

    method_summary = "; ".join(actions_taken) if actions_taken else "Standardized dataset format"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()
    cur = conn.cursor()
    for iss_id in issue_ids:
        cur.execute("""
            INSERT INTO recovery_logs (issue_id, method, approval_status, approved_by, retry_count, outcome, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (iss_id, method_summary, approval_status, approved_by, 1, "SUCCESS", ts))
        cur.execute("UPDATE issues SET status = 'Resolved' WHERE issue_id = ?", (iss_id,))
    conn.commit()
    conn.close()

    return cleaned_df, method_summary