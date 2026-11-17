import time
import streamlit as st
import pandas as pd
import plotly.express as px
from app.database import init_db, get_connection, log_run, log_issue
from app.validator import validate_dataset
from app.recovery import execute_recovery
from app.intelligence import (
    calculate_health_score,
    get_recurring_insights,
    get_kb_recommendation,
    build_team_notification,
)
from app.reporting import generate_audit_pdf

st.set_page_config(page_title="DataGuard Platform", layout="wide")
init_db()

# --- SIDEBAR: Role Switcher, Validation Mode & Navigation ---
st.sidebar.title("🛡️ DataGuard")
st.sidebar.caption("Intelligent Pipeline Reliability & Recovery")
user_role = st.sidebar.selectbox("Active Role (Approval Workflow)", ["Data Engineer", "Admin"])
schema_mode = st.sidebar.selectbox("Validation Mode", ["Auto-Detect Any CSV", "Orders Pipeline Schema"])
page = st.sidebar.radio(
    "Navigation",
    [
        "1. Upload & Failure Diagnosis",
        "2. Controlled Recovery & Approvals",
        "3. Team Issue Tracker & Audit Log",
        "4. Monitoring & Predictive Insights",
    ],
)

# ==========================================
# PAGE 1: UPLOAD, COMPARISON & DIAGNOSIS
# ==========================================
if page == "1. Upload & Failure Diagnosis":
    st.header("📤 Pipeline Execution & Failure Diagnosis")
    uploaded_file = st.file_uploader("Upload Dataset CSV", type=["csv"])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.subheader("Uploaded Dataset Preview")
        st.dataframe(df.head(10), use_container_width=True)

        if st.button("▶ Run DataGuard Pipeline", type="primary"):
            start_t = time.time()
            issues = validate_dataset(df, schema_mode)
            elapsed_ms = round((time.time() - start_t) * 1000, 2)

            if not issues:
                run_id = log_run(uploaded_file.name, len(df), len(df), 0, elapsed_ms, "SUCCESS")
                st.success(f"✅ Pipeline Run #{run_id} Succeeded! All {len(df)} records passed validation in {elapsed_ms} ms.")
            else:
                run_id = log_run(uploaded_file.name, len(df), 0, len(df), elapsed_ms, "FAILED")
                issue_ids = []
                for iss in issues:
                    iid = log_issue(run_id, iss["failure_type"], iss["severity"], iss["root_cause"])
                    issue_ids.append(iid)

                # Save active broken state in session for Recovery tab
                st.session_state["broken_df"] = df
                st.session_state["active_issues"] = issues
                st.session_state["active_issue_ids"] = issue_ids
                st.session_state["active_filename"] = uploaded_file.name

                st.error(f"❌ Pipeline Run #{run_id} Failed! {len(issues)} issue(s) detected.")

                # Feature 1: Consolidated Team Notification Preview
                alert = build_team_notification(uploaded_file.name, issues)
                with st.expander("🔔 Consolidated Team Notification Dispatched", expanded=True):
                    st.markdown(f"**Target:** `{alert['channel']}` | **Severity:** `{alert['severity']}`")
                    st.code(f"{alert['subject']}\n\n{alert['body']}")

                # Feature 10: Root Cause + Knowledge Base Solution
                st.subheader("🔍 Root Cause Diagnosis & Knowledge Base Fixes")
                for iss in issues:
                    with st.container(border=True):
                        st.markdown(f"**{iss['failure_type']}** — Severity: `{iss['severity']}`")
                        st.write(f"**Diagnosis:** {iss['root_cause']}")
                        st.info(f"💡 **Knowledge Base Recommendation:** {get_kb_recommendation(iss['failure_type'])}")

    # Feature 9: Pipeline Execution Comparison
    st.divider()
    st.subheader("⚖️ Pipeline Execution Comparison (Latest vs. Previous Run)")
    conn = get_connection()
    recent_runs = pd.read_sql_query("SELECT * FROM pipeline_runs ORDER BY run_id DESC LIMIT 2", conn)
    conn.close()
    if len(recent_runs) >= 2:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Latest Execution**")
            st.json(recent_runs.iloc[0].to_dict())
        with col2:
            st.markdown("**Previous Execution**")
            st.json(recent_runs.iloc[1].to_dict())
    else:
        st.caption("Run the pipeline at least twice to compare execution metrics.")

# ==========================================
# PAGE 2: RECOVERY & ADMIN APPROVAL WORKFLOW
# ==========================================
elif page == "2. Controlled Recovery & Approvals":
    st.header("🛠️ Assisted Recovery & Admin Approval Workflow")

    if "broken_df" not in st.session_state:
        st.info("No failed run awaiting recovery. Upload a broken CSV in Tab 1 first.")
    else:
        issues = st.session_state["active_issues"]
        df = st.session_state["broken_df"]
        issue_ids = st.session_state["active_issue_ids"]

        unrecoverable = [i for i in issues if not i["recoverable"]]
        sensitive = [i for i in issues if i["sensitive"]]

        if unrecoverable:
            st.error("⛔ Critical schema errors (e.g., Missing Columns) cannot be auto-recovered. Fix the source CSV and re-upload.")
        else:
            st.warning(f"Found {len(issues)} recoverable issue(s) in `{st.session_state['active_filename']}`.")
            if sensitive and user_role != "Admin":
                st.error("🔒 **Admin Approval Required:** This recovery drops rows with missing/negative values. Switch role to **Admin** in the left sidebar to approve and execute.")
            else:
                label = "✅ Approve & Execute Sensitive Recovery (Admin)" if sensitive else "⚡ Auto-Recover & Retry Pipeline"
                if st.button(label, type="primary"):
                    approval_mode = "ADMIN_APPROVED" if sensitive else "AUTO_APPROVED"
                    cleaned_df, summary = execute_recovery(df, issue_ids, user_role, approval_mode)
                    log_run(st.session_state["active_filename"] + " (Recovered)", len(df), len(cleaned_df), len(df) - len(cleaned_df), 12.5, "SUCCESS")
                    st.success(f"🎉 Recovery Succeeded! Actions taken: {summary}")
                    st.dataframe(cleaned_df, use_container_width=True)
                    del st.session_state["broken_df"]

    st.divider()
    st.subheader("📜 Recovery History Log")
    conn = get_connection()
    rec_df = pd.read_sql_query("SELECT * FROM recovery_logs ORDER BY recovery_id DESC", conn)
    conn.close()
    st.dataframe(rec_df, use_container_width=True)

# ==========================================
# PAGE 3: TEAM ISSUE TRACKER & AUDIT LOG
# ==========================================
elif page == "3. Team Issue Tracker & Audit Log":
    st.header("👥 Centralized Issue Tracking & Team Assignment")
    conn = get_connection()
    issues_df = pd.read_sql_query("SELECT * FROM issues ORDER BY issue_id DESC", conn)
    conn.close()

    if issues_df.empty:
        st.info("No issues logged yet.")
    else:
        st.dataframe(issues_df, use_container_width=True)
        st.subheader("Assign Issue & Add Investigation Notes")
        col1, col2, col3 = st.columns(3)
        with col1:
            selected_id = st.selectbox("Select Issue ID", issues_df["issue_id"].tolist())
        with col2:
            assignee = st.selectbox("Assign To", ["Unassigned", "Aarav (Data Eng)", "Priya (DevOps)", "Naga (Lead)"])
        with col3:
            priority = st.selectbox("Priority", ["Low", "Medium", "High", "Critical"])
        note = st.text_input("Investigation Notes")

        if st.button("Update Issue Assignment"):
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "UPDATE issues SET assigned_to = ?, priority = ?, notes = ? WHERE issue_id = ?",
                (assignee, priority, note, selected_id),
            )
            conn.commit()
            conn.close()
            st.success(f"Issue #{selected_id} updated!")
            st.rerun()

# ==========================================
# PAGE 4: MONITORING & PREDICTIVE INSIGHTS
# ==========================================
elif page == "4. Monitoring & Predictive Insights":
    st.header("📊 Pipeline Health & Predictive Failure Insights")

    conn = get_connection()
    runs_df = pd.read_sql_query("SELECT * FROM pipeline_runs", conn)
    issues_df = pd.read_sql_query("SELECT * FROM issues", conn)
    rec_df = pd.read_sql_query("SELECT * FROM recovery_logs", conn)
    conn.close()

    health = calculate_health_score()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🩺 Pipeline Health Score", f"{health}%")
    c2.metric("Total Runs", len(runs_df))
    c3.metric("Failed Runs", len(runs_df[runs_df["status"] == "FAILED"]) if not runs_df.empty else 0)
    c4.metric("Recovered Issues", len(rec_df))

    # Feature 5: Recurring Failure Intelligence
    st.subheader("🧠 Predictive Failure Insights (Recurring Patterns)")
    recurring = get_recurring_insights()
    if recurring.empty:
        st.success("No recurring failure patterns detected yet.")
    else:
        for _, row in recurring.iterrows():
            st.warning(
                f"⚠️ **Recurring Pattern Detected:** `{row['failure_type']}` has occurred **{row['occurrences']} times**. "
                f"**Preventive Action:** {get_kb_recommendation(row['failure_type'])}"
            )

    if not issues_df.empty:
        fig = px.bar(issues_df, x="failure_type", title="Failures by Category", color="severity")
        st.plotly_chart(fig, use_container_width=True)

    # Feature 7: Automated Audit Report Generation
    st.divider()
    st.subheader("📑 Export Audit Reports")
    col_pdf, col_csv = st.columns(2)
    with col_pdf:
        pdf_bytes = generate_audit_pdf()
        st.download_button("⬇ Download PDF Audit Report", data=pdf_bytes, file_name="DataGuard_Audit_Report.pdf", mime="application/pdf")
    with col_csv:
        st.download_button("⬇ Download CSV Issue Log", data=issues_df.to_csv(index=False), file_name="DataGuard_Issues.csv", mime="text/csv")