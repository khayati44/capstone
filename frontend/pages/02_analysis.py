"""
Page 2 — AI Analysis (3-Agent Pipeline)
"""

import streamlit as st
import time

st.set_page_config(page_title="AI Analysis", page_icon="🤖", layout="wide")

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from frontend.utils.ui_components import require_auth, get_token, metric_card, progress_steps, backend_status_indicator
from frontend.utils.api_client import APIClient

require_auth()
backend_status_indicator()

st.markdown("""
<div style='background: linear-gradient(90deg, #f093fb 0%, #f5576c 100%); padding: 30px; border-radius: 15px; margin-bottom: 30px;'>
    <h1 style='color: white; margin:0; font-size: 42px;'>🤖 AI Tax Analysis</h1>
    <p style='color: #f0f0f0; margin: 10px 0 0 0; font-size: 18px;'>Run the 3-agent AI pipeline to identify all eligible tax deductions</p>
</div>
""", unsafe_allow_html=True)

api = APIClient()
token = get_token()

# ─── Pipeline Steps Display ──────────────────────────────────────────────────
PIPELINE_STEPS = [
    {"label": "Upload Selected", "icon": "📤"},
    {"label": "Agent 1: Categorizer", "icon": "🏷️"},
    {"label": "Agent 2: Rule Matcher", "icon": "📚"},
    {"label": "Agent 3: Calculator", "icon": "🧮"},
    {"label": "Report Ready", "icon": "✅"},
]

# ─── Upload Selection ────────────────────────────────────────────────────────
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 📁 Select Upload to Analyze")

    uploads_result = api.get_uploads(token)
    upload_options = {}
    if uploads_result.get("success"):
        for u in uploads_result["data"]:
            label = f"#{u['id']} — {u['filename']} ({u['transaction_count']} transactions)"
            upload_options[u["id"]] = label

    if not upload_options:
        st.warning("No uploads found. Please upload a bank statement first.")
        st.stop()

    # Default to session upload ID if set
    default_idx = 0
    if st.session_state.get("current_upload_id") and st.session_state.current_upload_id in upload_options:
        default_idx = list(upload_options.keys()).index(st.session_state.current_upload_id)

    selected_upload_id = st.selectbox(
        "Choose upload",
        options=list(upload_options.keys()),
        format_func=lambda x: upload_options[x],
        index=default_idx,
    )

    st.session_state.current_upload_id = selected_upload_id

with col2:
    st.markdown("### 🤖 Pipeline Overview")
    st.markdown("""
    <div style='background:#E3F2FD; padding:16px; border-radius:10px;'>
        <b>Agent 1 — Transaction Categorizer</b><br>
        <small style='color:#555;'>Classifies each transaction by merchant type and purpose</small>
        <hr style='margin:8px 0;'>
        <b>Agent 2 — Tax Rule Matcher</b><br>
        <small style='color:#555;'>RAG-grounded matching to 80C/80D/80E/80G/24B sections</small>
        <hr style='margin:8px 0;'>
        <b>Agent 3 — Deduction Calculator</b><br>
        <small style='color:#555;'>Computes exact deductibles with section limits</small>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ─── Run Analysis Button ─────────────────────────────────────────────────────
st.markdown("### 🚀 Run Analysis")

col_btn, col_info = st.columns([1, 3])
with col_btn:
    run_analysis = st.button(
        "▶️ Start AI Analysis",
        type="primary",
        use_container_width=True,
        disabled=not selected_upload_id,
    )
with col_info:
    st.info(f"⏱️ Analysis typically takes 1-3 minutes depending on transaction count.")

if run_analysis:
    st.markdown("### ⚙️ Pipeline Progress")

    # Step indicators
    step_cols = st.columns(5)
    step_statuses = ["pending"] * 5

    def update_steps(current_step: int, placeholder):
        with placeholder.container():
            cols = st.columns(5)
            icons = ["📤", "🏷️", "📚", "🧮", "✅"]
            labels = ["Upload\nSelected", "Agent 1\nCategorizer", "Agent 2\nRule Matcher", "Agent 3\nCalculator", "Report\nReady"]
            for i, (col, icon, label) in enumerate(zip(cols, icons, labels)):
                with col:
                    if i < current_step:
                        st.markdown(f"""
                        <div style='text-align:center; background:#E8F5E9; padding:12px; border-radius:8px;'>
                            <div style='font-size:1.5rem;'>{icon}</div>
                            <div style='color:#4CAF50; font-weight:700; font-size:0.8rem;'>✅ Done</div>
                            <div style='color:#666; font-size:0.75rem;'>{label}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    elif i == current_step:
                        st.markdown(f"""
                        <div style='text-align:center; background:#E3F2FD; padding:12px; border-radius:8px; border:2px solid #2196F3;'>
                            <div style='font-size:1.5rem;'>{icon}</div>
                            <div style='color:#2196F3; font-weight:700; font-size:0.8rem;'>⏳ Running</div>
                            <div style='color:#666; font-size:0.75rem;'>{label}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style='text-align:center; background:#F5F5F5; padding:12px; border-radius:8px;'>
                            <div style='font-size:1.5rem; opacity:0.4;'>{icon}</div>
                            <div style='color:#999; font-size:0.8rem;'>Pending</div>
                            <div style='color:#ccc; font-size:0.75rem;'>{label}</div>
                        </div>
                        """, unsafe_allow_html=True)

    steps_placeholder = st.empty()
    update_steps(0, steps_placeholder)

    status_placeholder = st.empty()
    result_placeholder = st.empty()

    with status_placeholder.container():
        with st.spinner("🤖 Running Agent 1: Categorizing transactions..."):
            update_steps(1, steps_placeholder)
            result = api.analyze(token, selected_upload_id)

    update_steps(4, steps_placeholder)
    status_placeholder.empty()

    if result.get("success"):
        data = result["data"]
        report = data.get("report", {})

        with result_placeholder.container():
            st.success("✅ Analysis complete! All 3 agents finished successfully.")

            # Summary metrics
            st.markdown("### 📊 Analysis Summary")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                metric_card("Total Transactions", str(data.get("transaction_count", 0)), "Analyzed")
            with c2:
                metric_card("Tax Relevant", str(data.get("tax_relevant_count", 0)),
                             "Flagged by Agent 1", color="warning")
            with c3:
                metric_card("Sections Matched", str(data.get("matched_count", 0)),
                             "Matched by Agent 2", color="info")
            with c4:
                total = report.get("total_capped_deductions", 0)
                metric_card("Total Deductions", f"₹{total:,.0f}",
                             "Calculated by Agent 3", color="success")

            # Section breakdown
            summaries = report.get("section_summaries", [])
            if summaries:
                st.markdown("### 🏷️ Deductions by Section")
                section_cols = st.columns(min(len(summaries), 4))
                for i, summary in enumerate(summaries):
                    with section_cols[i % 4]:
                        metric_card(
                            f"Section {summary['section']}",
                            f"₹{summary['capped_deductible']:,.0f}",
                            f"{summary['transaction_count']} transactions",
                            color="info",
                        )

            # Tax savings estimate
            tax_20 = report.get("estimated_tax_saved_20_percent", 0)
            tax_30 = report.get("estimated_tax_saved_30_percent", 0)
            st.markdown("### 💰 Estimated Tax Savings")
            t1, t2 = st.columns(2)
            with t1:
                metric_card("Tax Saved @ 20% Slab", f"₹{tax_20:,.0f}",
                             "For income ₹5L–₹10L bracket", color="success")
            with t2:
                metric_card("Tax Saved @ 30% Slab", f"₹{tax_30:,.0f}",
                             "For income above ₹10L bracket", color="success")

            st.info("👉 Go to **💰 Deductions** page to view detailed line items and download report!")
    else:
        result_placeholder.error(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
