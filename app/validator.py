import pandas as pd

ORDERS_COLUMNS = ["Order ID", "Product", "Quantity", "Price", "Order Date"]

def validate_dataset(df: pd.DataFrame, schema_mode: str = "Auto-Detect Any CSV"):
    """
    Validates either:
    - 'Orders Pipeline Schema' (enforces the 5 exact order columns)
    - 'Auto-Detect Any CSV' (dynamically checks any uploaded CSV for nulls, duplicates, negative numbers, and bad dates)
    """
    issues = []

    if df.empty or len(df.columns) == 0:
        issues.append({
            "failure_type": "Empty Dataset",
            "severity": "CRITICAL",
            "root_cause": "The uploaded CSV file contains no rows or columns.",
            "sensitive": True,
            "recoverable": False
        })
        return issues

    # Mode 1: Strict Orders Schema Check
    if schema_mode == "Orders Pipeline Schema":
        missing_cols = [col for col in ORDERS_COLUMNS if col not in df.columns]
        if missing_cols:
            issues.append({
                "failure_type": "Missing Column",
                "severity": "CRITICAL",
                "root_cause": f"Required column(s) missing from uploaded file: {', '.join(missing_cols)}.",
                "sensitive": True,
                "recoverable": False
            })
            return issues

    # 2. Duplicate Records Check
    if "Order ID" in df.columns:
        dup_count = int(df.duplicated(subset=["Order ID"]).sum())
    else:
        dup_count = int(df.duplicated().sum())

    if dup_count > 0:
        issues.append({
            "failure_type": "Duplicate Records",
            "severity": "MEDIUM",
            "root_cause": f"Found {dup_count} duplicate record(s) in the dataset.",
            "sensitive": False,
            "recoverable": True
        })

    # 3. Missing / Null Values Check across all columns
    null_rows = int(df.isnull().any(axis=1).sum())
    if null_rows > 0:
        null_cols = [col for col in df.columns if df[col].isnull().any()]
        issues.append({
            "failure_type": "Missing Values",
            "severity": "HIGH",
            "root_cause": f"Found {null_rows} row(s) with empty values in column(s): {', '.join(null_cols)}.",
            "sensitive": True,
            "recoverable": True
        })

    # 4. Invalid Values Check (Negative numbers in numeric columns)
    numeric_cols = df.select_dtypes(include=["number"]).columns
    for col in numeric_cols:
        neg_count = int((df[col] < 0).sum())
        if neg_count > 0:
            issues.append({
                "failure_type": "Invalid Values",
                "severity": "HIGH",
                "root_cause": f"Found {neg_count} negative value(s) in numeric column '{col}'.",
                "sensitive": True,
                "recoverable": True
            })

    # 5. Invalid Date Format Check (Any column with 'date' in its name)
    date_cols = [col for col in df.columns if "date" in col.lower()]
    for col in date_cols:
        parsed_dates = pd.to_datetime(df[col], errors="coerce")
        bad_dates = int(parsed_dates.isnull().sum() - df[col].isnull().sum())
        if bad_dates > 0:
            issues.append({
                "failure_type": "Invalid Date Format",
                "severity": "MEDIUM",
                "root_cause": f"Found {bad_dates} unparseable date value(s) in column '{col}'.",
                "sensitive": False,
                "recoverable": True
            })

    return issues