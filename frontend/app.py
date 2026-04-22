"""
Streamlit Multi-Page App — Smart Tax Deduction Finder
Main entry point with auth and navigation.
"""

import streamlit as st

st.set_page_config(
    page_title="Smart Tax Deduction Finder",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Modern Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }
    [data-testid="stSidebar"] .stMarkdown, 
    [data-testid="stSidebar"] label {
        color: #ffffff !important;
        font-weight: 500;
    }

    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }

    /* Enhanced Cards */
    .metric-card {
        background: white;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        border-left: 5px solid #667eea;
        margin-bottom: 20px;
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 25px rgba(0,0,0,0.15);
    }
    .metric-card.warning {
        border-left-color: #f093fb;
    }
    .metric-card.info {
        border-left-color: #4facfe;
    }
    .metric-card.success {
        border-left-color: #43e97b;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }

    /* Headers */
    h1, h2, h3 {
        color: #1a1a2e;
    }

    /* Input fields */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border-radius: 8px;
        border: 1.5px solid #e0e0e0;
    }

    /* Success/error banners */
    .stSuccess, .stError, .stWarning, .stInfo {
        border-radius: 8px;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ─── Session State Initialization ────────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "current_upload_id" not in st.session_state:
    st.session_state.current_upload_id = None


# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🧾 Tax Deduction Finder")
    st.markdown("*AI-powered for Indian salaried employees*")
    st.divider()

    if st.session_state.authenticated and st.session_state.user:
        user = st.session_state.user
        st.markdown(f"👤 **{user.get('full_name', user.get('email', 'User'))}**")
        st.markdown(f"📧 {user.get('email', '')}")
        st.divider()

        st.markdown("### Navigation")
        st.page_link("pages/01_upload.py", label="📤 Upload Statement", icon="📤")
        st.page_link("pages/02_analysis.py", label="🤖 AI Analysis", icon="🤖")
        st.page_link("pages/03_deductions.py", label="💰 Deductions", icon="💰")
        st.page_link("pages/04_query.py", label="🔍 Smart Query", icon="🔍")
        st.divider()

        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.token = None
            st.session_state.user = None
            st.session_state.current_upload_id = None
            st.rerun()
    else:
        st.markdown("### 📌 Features")
        st.markdown("""
        - 📄 Bank statement OCR
        - 🤖 3-Agent AI pipeline
        - 🔍 RAG-powered tax matching
        - 💡 Section 80C/D/E/G analysis
        - 📊 Deduction reports
        - 💬 Natural language queries
        """)


# ─── Main Page (Login/Register) ───────────────────────────────────────────────
if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style='text-align:center; padding: 40px 0 20px 0;'>
            <h1 style='font-size:3rem;'>🧾</h1>
            <h1>Smart Tax Deduction Finder</h1>
            <p style='color:#666; font-size:1.1rem;'>
                AI-powered tax deduction analysis for Indian salaried employees.<br>
                Upload your bank statement → Get all deductions identified automatically.
            </p>
        </div>
        """, unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["🔐 Login", "✏️ Register"])

        from utils.api_client import APIClient
        api = APIClient()

        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="you@example.com")
                password = st.text_input("Password", type="password", placeholder="••••••••")
                submitted = st.form_submit_button("Login", use_container_width=True, type="primary")

                if submitted:
                    if not email or not password:
                        st.error("Please enter email and password")
                    else:
                        with st.spinner("Logging in..."):
                            result = api.login(email, password)
                        if result.get("success"):
                            st.session_state.token = result["token"]
                            # Fetch user profile
                            user_result = api.get_me(result["token"])
                            if user_result.get("success"):
                                st.session_state.user = user_result["user"]
                            st.session_state.authenticated = True
                            st.success("Login successful! Redirecting...")
                            st.rerun()
                        else:
                            st.error(f"Login failed: {result.get('error', 'Invalid credentials')}")

        with tab_register:
            with st.form("register_form"):
                full_name = st.text_input("Full Name", placeholder="Arjun Sharma")
                reg_email = st.text_input("Email", placeholder="arjun@example.com", key="reg_email")
                reg_password = st.text_input("Password", type="password",
                                             placeholder="Min 8 characters", key="reg_pass")
                reg_confirm = st.text_input("Confirm Password", type="password",
                                            placeholder="Repeat password", key="reg_confirm")
                reg_submitted = st.form_submit_button("Create Account", use_container_width=True,
                                                       type="primary")

                if reg_submitted:
                    if not reg_email or not reg_password:
                        st.error("Please fill all required fields")
                    elif reg_password != reg_confirm:
                        st.error("Passwords do not match")
                    elif len(reg_password) < 8:
                        st.error("Password must be at least 8 characters")
                    else:
                        with st.spinner("Creating account..."):
                            result = api.register(reg_email, reg_password, full_name)
                        if result.get("success"):
                            st.success("Account created! Please login.")
                        else:
                            st.error(f"Registration failed: {result.get('error', 'Unknown error')}")

else:
    st.markdown("""
    <div style='text-align:center; padding: 60px 20px;'>
        <h2>👋 Welcome back!</h2>
        <p style='color:#666;'>Use the sidebar to navigate to Upload, Analysis, Deductions, or Query.</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
        <div class='metric-card info'>
            <h3>📤 Step 1</h3>
            <p>Upload your bank statement PDF</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class='metric-card warning'>
            <h3>🤖 Step 2</h3>
            <p>Run AI Analysis (3-agent pipeline)</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class='metric-card success'>
            <h3>💰 Step 3</h3>
            <p>View identified tax deductions</p>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown("""
        <div class='metric-card'>
            <h3>🔍 Step 4</h3>
            <p>Query your transactions naturally</p>
        </div>
        """, unsafe_allow_html=True)
