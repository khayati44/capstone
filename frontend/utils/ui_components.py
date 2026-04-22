"""
Reusable Streamlit UI components.
"""

import streamlit as st
from typing import Optional


def require_auth() -> bool:
    """Check if user is authenticated. Shows warning if not."""
    if not st.session_state.get("authenticated"):
        st.warning("⚠️ Please login first from the Home page.")
        st.stop()
        return False
    return True


def get_token() -> str:
    """Get auth token from session state."""
    return st.session_state.get("token", "")


def metric_card(title: str, value: str, subtitle: str = "", color: str = "success"):
    """Render a styled metric card."""
    colors = {
        "success": "#4CAF50",
        "warning": "#FF9800",
        "info": "#2196F3",
        "danger": "#f44336",
    }
    border_color = colors.get(color, "#4CAF50")
    st.markdown(f"""
    <div style='background:white; border-radius:12px; padding:20px; 
                box-shadow:0 2px 12px rgba(0,0,0,0.08); 
                border-left:4px solid {border_color}; margin-bottom:12px;'>
        <p style='color:#666; margin:0; font-size:0.85rem; font-weight:600; 
                  text-transform:uppercase;'>{title}</p>
        <p style='color:#1a1a2e; margin:4px 0; font-size:1.8rem; font-weight:700;'>{value}</p>
        {f"<p style='color:#888; margin:0; font-size:0.8rem;'>{subtitle}</p>" if subtitle else ""}
    </div>
    """, unsafe_allow_html=True)


def section_badge(section: str) -> str:
    """Return colored HTML badge for tax section."""
    colors = {
        "80C": "#4CAF50",
        "80D": "#2196F3",
        "80E": "#9C27B0",
        "80G": "#FF5722",
        "80GG": "#FF9800",
        "24B": "#009688",
        "Section 37": "#607D8B",
        "NONE": "#9E9E9E",
    }
    color = colors.get(section, "#9E9E9E")
    return f"""<span style='background:{color}; color:white; padding:2px 8px; 
               border-radius:12px; font-size:0.75rem; font-weight:600;'>{section}</span>"""


def format_inr(amount: float) -> str:
    """Format amount in Indian Rupee notation."""
    if amount >= 1_00_00_000:  # 1 crore
        return f"₹{amount/1_00_00_000:.2f}Cr"
    elif amount >= 1_00_000:  # 1 lakh
        return f"₹{amount/1_00_000:.2f}L"
    else:
        return f"₹{amount:,.0f}"


def progress_steps(steps: list[dict], current: int):
    """Display a step progress indicator."""
    cols = st.columns(len(steps))
    for i, (col, step) in enumerate(zip(cols, steps)):
        with col:
            if i < current:
                st.markdown(f"""
                <div style='text-align:center; padding:10px;'>
                    <div style='background:#4CAF50; color:white; border-radius:50%; 
                                width:36px; height:36px; line-height:36px; 
                                margin:0 auto; font-weight:bold;'>✓</div>
                    <p style='color:#4CAF50; margin-top:6px; font-size:0.85rem; 
                              font-weight:600;'>{step['label']}</p>
                </div>
                """, unsafe_allow_html=True)
            elif i == current:
                st.markdown(f"""
                <div style='text-align:center; padding:10px;'>
                    <div style='background:#2196F3; color:white; border-radius:50%; 
                                width:36px; height:36px; line-height:36px; 
                                margin:0 auto; font-weight:bold;'>{i+1}</div>
                    <p style='color:#2196F3; margin-top:6px; font-size:0.85rem; 
                              font-weight:600;'>{step['label']}</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style='text-align:center; padding:10px;'>
                    <div style='background:#E0E0E0; color:#999; border-radius:50%; 
                                width:36px; height:36px; line-height:36px; 
                                margin:0 auto; font-weight:bold;'>{i+1}</div>
                    <p style='color:#999; margin-top:6px; font-size:0.85rem;'>{step['label']}</p>
                </div>
                """, unsafe_allow_html=True)


def backend_status_indicator():
    """Show backend connection status."""
    from frontend.utils.api_client import APIClient
    api = APIClient()
    result = api.health()
    if result.get("success"):
        st.sidebar.success("🟢 Backend connected")
    else:
        st.sidebar.error("🔴 Backend offline")
