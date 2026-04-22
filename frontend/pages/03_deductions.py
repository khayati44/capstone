"""
Page 3 — Deductions Report
Shows summary cards, detailed table, bar chart, and CSV download.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import io
import json

st.set_page_config(page_title="Deductions Report", page_icon="💰", layout="wide")

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from frontend.utils.ui_components import (require_auth, get_token, metric_card,
                                           section_badge, format_inr, backend_status_indicator)
from frontend.utils.api_client import APIClient

require_auth()
backend_status_indicator()

st.markdown("""
<div style='background: linear-gradient(90deg, #43e97b 0%, #38f9d7 100%); padding: 30px; border-radius: 15px; margin-bottom: 30px;'>
    <h1 style='color: white; margin:0; font-size: 42px;'>💰 Tax Deductions Report</h1>
    <p style='color: #f0f0f0; margin: 10px 0 0 0; font-size: 18px;'>View all identified tax deductions, section breakdown, and estimated savings</p>
</div>
""", unsafe_allow_html=True)

api = APIClient()
token = get_token()

# ─── Upload Selection ────────────────────────────────────────────────────────
uploads_result = api.get_uploads(token)
upload_options = {}
if uploads_result.get("success"):
    for u in uploads_result["data"]:
        label = f"#{u['id']} — {u['filename']}"
        upload_options[u["id"]] = label

if not upload_options:
    st.warning("No uploads found. Please upload a bank statement first.")
    st.stop()

default_idx = 0
if st.session_state.get("current_upload_id") and st.session_state.current_upload_id in upload_options:
    default_idx = list(upload_options.keys()).index(st.session_state.current_upload_id)

selected_upload_id = st.selectbox(
    "Select upload",
    options=list(upload_options.keys()),
    format_func=lambda x: upload_options[x],
    index=default_idx,
)

# ─── Fetch Deductions ─────────────────────────────────────────────────────────
deductions_result = api.get_deductions(token, selected_upload_id)

if not deductions_result.get("success"):
    error_msg = deductions_result.get("error", "Unknown error")
    if "404" in str(error_msg) or "not found" in str(error_msg).lower():
        st.warning("⚠️ No analysis found for this upload. Please run AI Analysis first.")
        st.page_link("pages/02_analysis.py", label="👉 Go to AI Analysis", icon="🤖")
    else:
        st.error(f"Error loading deductions: {error_msg}")
    st.stop()

data = deductions_result["data"]
report = data.get("report", {})

# ─── Summary Cards ────────────────────────────────────────────────────────────
st.markdown("### 📊 Summary")
c1, c2, c3, c4 = st.columns(4)
with c1:
    total_ded = data.get("total_deductions", 0)
    metric_card("Total Deductions Found", format_inr(total_ded), "After applying section limits", color="success")
with c2:
    tax_20 = data.get("estimated_tax_saved_20", 0)
    metric_card("Tax Saved @ 20%", format_inr(tax_20), "For ₹5L–₹10L income slab", color="info")
with c3:
    tax_30 = data.get("estimated_tax_saved_30", 0)
    metric_card("Tax Saved @ 30%", format_inr(tax_30), "For income above ₹10L", color="warning")
with c4:
    sections = data.get("sections_covered", [])
    metric_card("Sections Covered", str(len(sections)), ", ".join(sections) if sections else "None")

st.divider()

# ─── Bar Chart: Deductions by Section ────────────────────────────────────────
summaries = report.get("section_summaries", [])
if summaries:
    st.markdown("### 📈 Deductions by Section")
    chart_data = pd.DataFrame([{
        "Section": s["section"],
        "Gross Deductible (₹)": s["total_deductible"],
        "Capped Deductible (₹)": s["capped_deductible"],
        "Transactions": s["transaction_count"],
    } for s in summaries])

    col_chart, col_table = st.columns([3, 2])
    with col_chart:
        fig = px.bar(
            chart_data,
            x="Section",
            y=["Gross Deductible (₹)", "Capped Deductible (₹)"],
            barmode="group",
            title="Gross vs Capped Deductions by Section",
            color_discrete_map={
                "Gross Deductible (₹)": "#90CAF9",
                "Capped Deductible (₹)": "#1565C0",
            },
            template="plotly_white",
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font={"color": "#1a1a2e"},
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_table:
        st.markdown("**Section Limits Reference**")
        limits_data = {
            "80C": "₹1,50,000",
            "80D": "₹25,000/₹50,000",
            "80E": "No limit",
            "80G": "50%-100%",
            "80GG": "₹60,000/year",
            "24B": "₹2,00,000",
            "Section 37": "No limit",
        }
        limits_df = pd.DataFrame(list(limits_data.items()), columns=["Section", "Limit"])
        st.dataframe(limits_df, hide_index=True, use_container_width=True)

    st.divider()

# ─── Detailed Transaction Table ───────────────────────────────────────────────
st.markdown("### 📋 Detailed Deduction Line Items")

line_items = report.get("line_items", [])
if line_items:
    filter_col, download_col = st.columns([3, 1])
    with filter_col:
        search_text = st.text_input("🔍 Filter by description or section", placeholder="e.g., LIC, 80C, insurance")

    table_data = []
    for item in line_items:
        row = {
            "Date": item.get("date", "—"),
            "Description": (item.get("description") or "")[:60],
            "Amount (₹)": f"₹{item.get('amount', 0):,.0f}",
            "Section": item.get("section", "—"),
            "Deduction %": f"{item.get('deduction_percentage', 0):.0f}%",
            "Deductible (₹)": f"₹{item.get('deductible_amount', 0):,.2f}",
            "Conditions": (item.get("conditions") or "")[:80],
        }
        table_data.append(row)

    df = pd.DataFrame(table_data)

    # Apply search filter
    if search_text:
        mask = (
            df["Description"].str.contains(search_text, case=False, na=False) |
            df["Section"].str.contains(search_text, case=False, na=False)
        )
        df = df[mask]

    st.dataframe(df, use_container_width=True, hide_index=True)

    # ─── CSV Download ─────────────────────────────────────────────────────────
    with download_col:
        st.markdown("")  # spacer
        csv_buf = io.StringIO()
        pd.DataFrame(table_data).to_csv(csv_buf, index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv_buf.getvalue(),
            file_name=f"tax_deductions_upload_{selected_upload_id}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # Download full report JSON
    st.download_button(
        label="📄 Download Full Report (JSON)",
        data=json.dumps(report, indent=2),
        file_name=f"tax_report_upload_{selected_upload_id}.json",
        mime="application/json",
    )
else:
    st.info("No deduction line items found. The transactions may not have tax-relevant payments.")

st.divider()

# ─── All Transactions Table ────────────────────────────────────────────────────
with st.expander("📜 View All Transactions (including non-deductible)"):
    tx_result = api.get_deduction_transactions(token, selected_upload_id, tax_relevant_only=False)
    if tx_result.get("success"):
        txns = tx_result["data"]
        if txns:
            tx_df = pd.DataFrame([{
                "Date": t.get("date", "—"),
                "Description": (t.get("description") or "")[:60],
                "Debit (₹)": f"₹{t.get('debit_amount', 0):,.0f}" if t.get("debit_amount") else "—",
                "Credit (₹)": f"₹{t.get('credit_amount', 0):,.0f}" if t.get("credit_amount") else "—",
                "Tax Relevant": "✅" if t.get("is_tax_relevant") else "—",
                "Section": t.get("matched_section") or "—",
                "Deductible (₹)": f"₹{t.get('deductible_amount', 0):,.0f}" if t.get("deductible_amount") else "—",
            } for t in txns])
            st.dataframe(tx_df, use_container_width=True, hide_index=True)
        else:
            st.info("No transactions found.")
