"""
Page 1 — Upload Bank Statement PDF
"""

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Upload Statement", page_icon="📤", layout="wide")

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from frontend.utils.ui_components import require_auth, get_token, metric_card, backend_status_indicator
from frontend.utils.api_client import APIClient

require_auth()
backend_status_indicator()

st.markdown("""
<div style='background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 15px; margin-bottom: 30px;'>
    <h1 style='color: white; margin:0; font-size: 42px;'>📤 Upload Bank Statement</h1>
    <p style='color: #f0f0f0; margin: 10px 0 0 0; font-size: 18px;'>Upload your bank statement PDF to extract transactions via AI-powered OCR</p>
</div>
""", unsafe_allow_html=True)

api = APIClient()
token = get_token()

# DEBUG: Show authentication state and token for troubleshooting
st.write("DEBUG: Authenticated =", st.session_state.get("authenticated"))
st.write("DEBUG: Token =", token)

# ─── Upload Section ──────────────────────────────────────────────────────────
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 📄 Upload PDF")
    uploaded_file = st.file_uploader(
        "Drag & drop your bank statement PDF here",
        type=["pdf"],
        help="Supported banks: HDFC, SBI, ICICI. Max size: 10MB",
    )

    if uploaded_file is not None:
        file_size_kb = len(uploaded_file.getvalue()) / 1024
        st.info(f"📎 **{uploaded_file.name}** — {file_size_kb:.1f} KB")

        if st.button("🚀 Upload & Extract Transactions", type="primary", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()

            status_text.text("📤 Uploading PDF...")
            progress_bar.progress(20)

            result = api.upload_pdf(token, uploaded_file.getvalue(), uploaded_file.name)
            progress_bar.progress(60)

            if result.get("success"):
                data = result["data"]
                progress_bar.progress(100)
                status_text.text("✅ Processing complete!")

                st.success(f"✅ Successfully extracted **{data['transaction_count']}** transactions!")

                # Store upload ID in session
                st.session_state.current_upload_id = data["id"]

                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    metric_card("Transactions Found", str(data["transaction_count"]), "Extracted from PDF")
                with col_b:
                    metric_card("Bank Detected", data.get("bank_name", "Unknown"),
                                "Auto-detected format", color="info")
                with col_c:
                    metric_card("Status", data["status"].title(), "Upload status", color="success")

                st.info("👉 Go to **🤖 AI Analysis** to run the tax deduction analysis!")
            else:
                progress_bar.progress(0)
                status_text.empty()
                st.error(f"❌ Upload failed: {result.get('error', 'Unknown error')}")

with col2:
    st.markdown("### 💡 Tips")
    st.markdown("""
    **Supported Banks:**
    - 🏦 HDFC Bank
    - 🏦 State Bank of India (SBI)
    - 🏦 ICICI Bank
    - 🏦 Axis Bank
    - 🏦 Most Indian banks

    **Best Results:**
    - Use official bank-generated PDFs
    - Avoid scanned/photographed statements
    - Include full financial year data
    - Max file size: 10MB

    **Privacy:**
    - Account numbers are auto-redacted
    - PII removed before storage
    - Data stays on your server
    """)

    st.markdown("### 🔐 Security")
    st.markdown("""
    <div style='background:#E8F5E9; padding:12px; border-radius:8px;'>
        ✅ PII auto-redacted via Presidio<br>
        ✅ JWT authentication required<br>
        ✅ Data stored locally (SQLite)
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ─── Previous Uploads ─────────────────────────────────────────────────────────
st.markdown("### 📚 Previous Uploads")

uploads_result = api.get_uploads(token)
if uploads_result.get("success"):
    uploads = uploads_result["data"]
    if uploads:
        upload_df = pd.DataFrame([{
            "ID": u["id"],
            "Filename": u["filename"],
            "Bank": u.get("bank_name", "Unknown"),
            "Transactions": u["transaction_count"],
            "Status": u["status"].title(),
            "Uploaded": u["created_at"][:10] if u.get("created_at") else "—",
        } for u in uploads])

        st.dataframe(upload_df, use_container_width=True, hide_index=True)

        selected_id = st.selectbox(
            "Select upload to analyze",
            options=[u["id"] for u in uploads],
            format_func=lambda x: next(
                (f"#{u['id']} — {u['filename']} ({u['transaction_count']} txns)" for u in uploads if u["id"] == x), str(x)
            ),
        )
        if st.button("📌 Set as Active Upload", use_container_width=True):
            st.session_state.current_upload_id = selected_id
            st.success(f"Active upload set to ID #{selected_id}. Navigate to Analysis.")
    else:
        st.info("No uploads yet. Upload your first bank statement above!")
else:
    st.warning("Could not load previous uploads.")
