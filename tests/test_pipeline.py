import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from app.validator import validate_dataset
from app.recovery import execute_recovery
from app.database import init_db, log_run, log_issue

def test_valid_dataset_passes():
    df = pd.DataFrame({
        "Order ID": [1, 2],
        "Product": ["Laptop", "Mouse"],
        "Quantity": [1, 3],
        "Price": [50000, 500],
        "Order Date": ["2026-11-10", "2026-11-11"]
    })
    issues = validate_dataset(df, schema_mode="Orders Pipeline Schema")
    assert len(issues) == 0

def test_missing_column_detected():
    df = pd.DataFrame({
        "Order ID": [1],
        "Product": ["Laptop"],
        "Quantity": [1]
    })
    issues = validate_dataset(df, schema_mode="Orders Pipeline Schema")
    assert len(issues) == 1
    assert issues[0]["failure_type"] == "Missing Column"
    assert issues[0]["recoverable"] is False

def test_any_csv_detects_duplicates_and_negative_values():
    df = pd.DataFrame({
        "Patient_ID": [101, 101, 102],
        "Age": [25, 25, -5]
    })
    issues = validate_dataset(df, schema_mode="Auto-Detect Any CSV")
    types = [i["failure_type"] for i in issues]
    assert "Duplicate Records" in types
    assert "Invalid Values" in types

def test_auto_recovery_cleans_data():
    init_db()
    df = pd.DataFrame({
        "Order ID": [101, 101, 102],
        "Product": ["Laptop", "Laptop", "Phone"],
        "Quantity": [1, 1, -2],
        "Price": [45000, 45000, 15000],
        "Order Date": ["2026-11-10", "2026-11-10", "2026-11-11"]
    })
    run_id = log_run("test.csv", 3, 0, 3, 5.0, "FAILED")
    issue_id = log_issue(run_id, "Duplicate Records", "MEDIUM", "Test duplicate")
    cleaned_df, _ = execute_recovery(df, [issue_id], "Admin", "ADMIN_APPROVED")
    assert len(cleaned_df) == 1