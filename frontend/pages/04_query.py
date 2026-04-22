"""
Page 4 — Smart Query (Text-to-SQL)
Natural language questions about transactions.
"""

import streamlit as st

st.set_page_config(page_title="Smart Query", page_icon="🔍", layout="wide")

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from frontend.utils.ui_components import require_auth, get_token, backend_status_indicator
from frontend.utils.api_client import APIClient

require_auth()
backend_status_indicator()

st.markdown("""
<div style='background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%); padding: 30px; border-radius: 15px; margin-bottom: 30px;'>
    <h1 style='color: white; margin:0; font-size: 42px;'>🔍 Smart Transaction Query</h1>
    <p style='color: #f0f0f0; margin: 10px 0 0 0; font-size: 18px;'>Ask natural language questions about your transactions — powered by Text-to-SQL AI</p>
</div>
""", unsafe_allow_html=True)

api = APIClient()
token = get_token()

# ─── Example Queries ──────────────────────────────────────────────────────────
EXAMPLE_QUERIES = [
    "How much did I spend on insurance?",
    "Show me all my PPF contributions",
    "What is my total deduction under 80C?",
    "How many transactions do I have?",
    "What was my highest expense?",
    "Show all tax relevant transactions",
    "What are my total deductions by tax section?",
    "Show me all home loan payments",
]

col1, col2 = st.columns([3, 2])

with col1:
    st.markdown("### 💬 Ask a Question")

    # Check if example was selected
    auto_run = False
    if "query_example" in st.session_state:
        default_question = st.session_state.pop("query_example")
        auto_run = True
    else:
        default_question = ""

    # Query input
    question = st.text_area(
        "Enter your question",
        value=default_question,
        placeholder="e.g., What is the total health insurance premium paid this year?",
        height=100,
        key="question_input"
    )

    col_btn, col_clear = st.columns([2, 1])
    with col_btn:
        # Use only supported st.button parameters to avoid runtime errors
        run_query = st.button("🔍 Run Query", disabled=not question.strip(), use_container_width=True)
    with col_clear:
        if st.button("🗑️ Clear", use_container_width=True):
            st.rerun()

    if (run_query or auto_run) and question.strip():
        with st.spinner("🤖 Generating SQL and querying database..."):
            try:
                result = api.query(token, question)
            except Exception as e:
                st.error(f"❌ Failed to connect to backend: {str(e)}")
                st.info("💡 Please make sure the backend is running at http://localhost:8000")
                result = {"success": False, "error": str(e)}

        if result.get("success"): 
            data = result["data"]

            st.markdown("### 💡 Answer")
            answer_text = data.get('answer', 'No answer generated')
            st.markdown(f"""
            <div style='background:#E8F5E9; padding:20px; border-radius:12px; 
                        border-left:5px solid #4CAF50; margin-bottom:20px;'>
                <p style='margin:0; font-size:1.1rem; color:#1a1a2e; font-weight:500;'>{answer_text}</p>
            </div>
            """, unsafe_allow_html=True)

            # SQL query expandable - ALWAYS show
            sql_query = data.get("sql", "")
            if sql_query:
                with st.expander("🔎 View Generated SQL Query", expanded=True):
                    st.code(sql_query, language="sql")
            
            # Result data display
            import pandas as pd
            result_data = data.get("result", "")
            sql_query = data.get("sql", "")
            
            with st.expander("📊 Database Query Results", expanded=True):
                if result_data:
                    # Try to parse result_data as a table
                    table = None
                    try:
                        if isinstance(result_data, str):
                            # Try to evaluate string as Python literal
                            import ast
                            try:
                                result_data = ast.literal_eval(result_data)
                            except:
                                pass
                        
                        if isinstance(result_data, (list, tuple)) and len(result_data) > 0:
                            # List of rows (possibly tuples or dicts)
                            if isinstance(result_data[0], dict):
                                # List of dicts - direct conversion
                                table = pd.DataFrame(result_data)
                            elif isinstance(result_data[0], (list, tuple)):
                                # List of tuples - extract column names from SQL if possible
                                import re
                                columns = None
                                if sql_query:
                                    # Try to extract column names from SELECT statement
                                    select_match = re.search(r'SELECT\s+(.+?)\s+FROM', sql_query, re.IGNORECASE | re.DOTALL)
                                    if select_match:
                                        cols_str = select_match.group(1)
                                        if cols_str.strip() != '*':
                                            columns = [c.strip().split()[-1].strip('"') for c in cols_str.split(',')]
                                
                                if columns and len(columns) == len(result_data[0]):
                                    table = pd.DataFrame(result_data, columns=columns)
                                else:
                                    table = pd.DataFrame(result_data)
                            else:
                                # Single value per row
                                table = pd.DataFrame(result_data, columns=['Value'])
                        elif isinstance(result_data, dict):
                            table = pd.DataFrame([result_data])
                        elif isinstance(result_data, (int, float, str)) and not isinstance(result_data, bool):
                            # Single scalar value
                            table = pd.DataFrame([{'Result': result_data}])
                    except Exception as e:
                        st.warning(f"Could not parse result as table: {e}")
                    
                    # Display table or raw result
                    if table is not None and not table.empty:
                        st.dataframe(table, use_container_width=True)
                        st.caption(f"✅ Found {len(table)} row(s)")
                    else:
                        st.markdown("**Raw Result:**")
                        st.code(str(result_data), language="text")
                else:
                    st.info("ℹ️ Query executed successfully but returned no data.")
        else:
            error_msg = result.get('error', 'Unknown error occurred')
            st.error(f"❌ Query failed: {error_msg}")
            st.info("💡 Try rephrasing your question or use one of the example queries below.")

with col2:
    st.markdown("### 📝 Example Queries")
    st.markdown("Click any example to populate the query box:")

    for example in EXAMPLE_QUERIES:
        if st.button(f"▸ {example}", use_container_width=True, key=f"ex_{hash(example)}"):
            st.session_state["query_example"] = example
            st.rerun()

    # Apply selected example 
    if "query_example" in st.session_state:
        selected_example = st.session_state.pop("query_example")
        st.info(f"Selected: *{selected_example}*")

    st.divider()
    st.markdown("### 💡 Query Tips")
    st.markdown("""
    **You can ask about:**
    - Specific payment types (insurance, rent, EMI)
    - Date ranges (monthly, quarterly, FY)
    - Amount filters (above/below a threshold)
    - Tax sections (80C, 80D, etc.)
    - Merchant names or transaction descriptions
    
    **The AI will:**
    1. Convert your question to SQL
    2. Query your transaction database
    3. Summarize the results in plain English
    """)

    st.markdown("### 🗄️ Database Schema")
    with st.expander("View transactions table schema"):
        st.code("""
transactions
─────────────────────────────
id                  INTEGER
user_id             INTEGER
upload_id           INTEGER
date                TEXT
description         TEXT
debit_amount        REAL
credit_amount       REAL
balance             REAL
merchant_type       TEXT      -- AI categorized (e.g., Insurance, PPF)
likely_purpose      TEXT      -- AI determined purpose
is_tax_relevant     BOOLEAN   -- True if tax deductible
matched_section     TEXT      -- Tax section (80C, 80D, etc.)
deduction_percentage REAL     -- % deductible
conditions          TEXT      -- Tax conditions
deductible_amount   REAL      -- Amount you can deduct
        """, language="sql")
