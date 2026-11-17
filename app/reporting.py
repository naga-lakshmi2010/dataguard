from fpdf import FPDF
import pandas as pd
from app.database import get_connection
from app.intelligence import calculate_health_score

def generate_audit_pdf():
    conn = get_connection()
    runs = pd.read_sql_query("SELECT * FROM pipeline_runs ORDER BY run_id DESC LIMIT 10", conn)
    issues = pd.read_sql_query("SELECT * FROM issues ORDER BY issue_id DESC LIMIT 15", conn)
    conn.close()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "DataGuard - Automated Pipeline Audit Report", ln=True)

    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 8, f"Current Pipeline Health Score: {calculate_health_score()}%", ln=True)
    pdf.cell(0, 8, f"Total Recorded Runs: {len(runs)} | Total Logged Issues: {len(issues)}", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Recent Issues & Resolution Status:", ln=True)
    pdf.set_font("Arial", "", 10)
    for _, row in issues.iterrows():
        line = f"#{row['issue_id']} | {row['failure_type']} ({row['severity']}) | Assigned: {row['assigned_to']} | Status: {row['status']}"
        pdf.cell(0, 7, line, ln=True)

    return bytes(pdf.output())