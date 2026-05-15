"""
GeoMarketGPT — Institutional-Grade Geopolitical Intelligence Dashboard
Bloomberg/Palantir-style dark UI with live updates, interactive charts, AI reasoning.
"""

from __future__ import annotations

import sys
from pathlib import Path
# Add project root to sys.path to allow absolute imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import streamlit as st

from frontend.config import settings
from frontend.utils.api_client import api_client

st.set_page_config(
    page_title=f"{settings.APP_NAME} | Intelligence Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)


INJECTED_CSS = False


def inject_css() -> None:
    global INJECTED_CSS
    if INJECTED_CSS:
        return
    INJECTED_CSS = True
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

        /* ── Global ── */
        html, body, [class*="css"] {
            font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        .stApp {
            background: radial-gradient(circle at top right, #0d1b2a 0%, #0a0e17 60%, #05080f 100%);
            background-attachment: fixed;
            color: #e0e6ed;
        }
        
        .main > div {
            padding: 0 1.5rem 1.5rem 1.5rem;
        }
        
        .block-container {
            padding-top: 2rem !important;
            max-width: 100% !important;
        }

        /* ── Sidebar ── */
        section[data-testid="stSidebar"] {
            background: rgba(13, 17, 23, 0.6) !important;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-right: 1px solid rgba(255,255,255,0.08);
            width: 280px !important;
            box-shadow: 4px 0 24px rgba(0,0,0,0.4);
        }
        
        /* Hide the default Streamlit auto-generated page navigation */
        [data-testid="stSidebarNav"] {
            display: none !important;
        }
        
        section[data-testid="stSidebar"] .stButton button {
            background: rgba(255,255,255,0.03) !important;
            border: 1px solid rgba(255,255,255,0.05);
            color: #a0aec0 !important;
            display: flex !important;
            justify-content: flex-start !important;
            align-items: center !important;
            font-size: 0.9rem;
            font-weight: 500;
            padding: 10px 16px;
            border-radius: 8px;
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
            margin-bottom: 4px;
            width: 100%;
        }
        
        section[data-testid="stSidebar"] .stButton button p {
            text-align: left !important;
            margin: 0 !important;
            width: 100%;
        }
        
        section[data-testid="stSidebar"] .stButton button:hover {
            background: rgba(56, 189, 248, 0.1) !important;
            border-color: rgba(56, 189, 248, 0.4);
            color: #f8fafc !important;
            transform: translateX(4px);
            box-shadow: 0 4px 12px rgba(56, 189, 248, 0.15);
        }
        
        section[data-testid="stSidebar"] .stButton button[kind="primary"] {
            background: linear-gradient(90deg, rgba(14, 165, 233, 0.2) 0%, rgba(2, 132, 199, 0.1) 100%) !important;
            border-left: 3px solid #0ea5e9 !important;
            border-top: 1px solid rgba(14, 165, 233, 0.3) !important;
            border-right: 1px solid rgba(14, 165, 233, 0.3) !important;
            border-bottom: 1px solid rgba(14, 165, 233, 0.3) !important;
            color: #f8fafc !important;
            font-weight: 600;
            box-shadow: inset 0 0 12px rgba(14, 165, 233, 0.1);
        }

        /* ── Metric cards (Glassmorphism + Hover) ── */
        div[data-testid="stMetric"] {
            background: rgba(30, 41, 59, 0.4);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-top: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 12px;
            padding: 16px 20px;
            transition: all 0.3s ease;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
            position: relative;
            overflow: hidden;
        }
        
        div[data-testid="stMetric"]:hover {
            transform: translateY(-4px);
            box-shadow: 0 12px 40px rgba(14, 165, 233, 0.15);
            border-color: rgba(56, 189, 248, 0.3);
        }
        
        /* Subtle shine effect on metric cards */
        div[data-testid="stMetric"]::before {
            content: '';
            position: absolute;
            top: 0; left: -100%;
            width: 50%; height: 100%;
            background: linear-gradient(to right, transparent, rgba(255,255,255,0.05), transparent);
            transform: skewX(-25deg);
            transition: 0.5s;
        }
        div[data-testid="stMetric"]:hover::before {
            left: 150%;
        }

        div[data-testid="stMetric"] label {
            color: #94a3b8 !important;
            font-size: 0.75rem !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 6px;
        }
        
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
            color: #f8fafc !important;
            font-size: 1.8rem !important;
            font-weight: 700 !important;
            text-shadow: 0 2px 10px rgba(0,0,0,0.5);
            background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        /* ── Dividers ── */
        hr {
            border: 0;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent) !important;
            margin: 1.5rem 0 !important;
        }

        /* ── Expanders ── */
        details {
            background: rgba(15, 23, 42, 0.4);
            border: 1px solid rgba(255,255,255,0.05);
            border-radius: 10px;
            padding: 6px 16px;
            transition: all 0.3s ease;
        }
        details:hover {
            border-color: rgba(255,255,255,0.15);
            background: rgba(15, 23, 42, 0.6);
        }
        summary {
            color: #cbd5e1 !important;
            font-weight: 500;
            padding: 8px 0;
        }

        /* ── Tabs ── */
        button[data-baseweb="tab"] {
            color: #64748b !important;
            font-size: 0.9rem !important;
            font-weight: 600 !important;
            transition: color 0.2s ease;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        button[data-baseweb="tab"]:hover {
            color: #94a3b8 !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #38bdf8 !important;
            text-shadow: 0 0 12px rgba(56, 189, 248, 0.4);
        }
        div[data-baseweb="tab-highlight"] {
            background-color: #38bdf8 !important;
            box-shadow: 0 0 10px #38bdf8;
        }

        /* ── Select boxes / inputs ── */
        div[data-baseweb="select"] > div, input, textarea {
            background: rgba(15, 23, 42, 0.5) !important;
            border-color: rgba(255,255,255,0.1) !important;
            color: #f1f5f9 !important;
            border-radius: 8px !important;
            transition: all 0.2s ease;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.2);
        }
        div[data-baseweb="select"] > div:hover, input:hover, textarea:hover {
            border-color: rgba(56, 189, 248, 0.4) !important;
            background: rgba(15, 23, 42, 0.7) !important;
        }
        div[data-baseweb="select"] > div:focus-within, input:focus, textarea:focus {
            border-color: #38bdf8 !important;
            box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2), inset 0 2px 4px rgba(0,0,0,0.2) !important;
        }

        /* ── Primary Buttons ── */
        .stButton button[kind="primary"] {
            background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%) !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
            border-top: 1px solid rgba(255,255,255,0.2) !important;
            color: white !important;
            font-weight: 600 !important;
            letter-spacing: 0.5px;
            border-radius: 8px !important;
            padding: 8px 24px !important;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
        }
        .stButton button[kind="primary"]:hover {
            transform: translateY(-2px) scale(1.02);
            box-shadow: 0 8px 20px rgba(37, 99, 235, 0.5), 0 0 15px rgba(14, 165, 233, 0.4);
            background: linear-gradient(135deg, #38bdf8 0%, #1d4ed8 100%) !important;
        }
        .stButton button[kind="primary"]:active {
            transform: translateY(1px);
            box-shadow: 0 2px 5px rgba(37, 99, 235, 0.3);
        }

        /* ── Spinner ── */
        .stSpinner > div {
            border-color: #38bdf8 transparent transparent transparent !important;
        }

        /* ── Scrollbar ── */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: rgba(15, 23, 42, 0.5); }
        ::-webkit-scrollbar-thumb { background: rgba(51, 65, 85, 0.8); border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(71, 85, 105, 1); }

        /* ── Pipeline status dots ── */
        .pipeline-dot {
            display: inline-block;
            width: 8px; height: 8px;
            border-radius: 50%;
            margin-right: 6px;
            box-shadow: 0 0 8px currentColor;
        }
        .dot-healthy { color: #10b981; animation: pulse-healthy 2s infinite; }
        .dot-running { color: #38bdf8; animation: pulse-running 1.5s infinite; }
        .dot-idle { color: #64748b; }
        
        @keyframes pulse-healthy {
            0% { opacity: 0.6; box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
            50% { opacity: 1; box-shadow: 0 0 0 4px rgba(16, 185, 129, 0); }
            100% { opacity: 0.6; box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }
        @keyframes pulse-running {
            0% { opacity: 0.6; box-shadow: 0 0 0 0 rgba(56, 189, 248, 0.4); transform: scale(0.9); }
            50% { opacity: 1; box-shadow: 0 0 0 6px rgba(56, 189, 248, 0); transform: scale(1.1); }
            100% { opacity: 0.6; box-shadow: 0 0 0 0 rgba(56, 189, 248, 0); transform: scale(0.9); }
        }

        /* ── Container boxes ── */
        div[data-testid="stVerticalBlock"] > div > div[data-testid="stVerticalBlock"] {
            background: rgba(30, 41, 59, 0.2);
            border: 1px solid rgba(255,255,255,0.03);
            border-radius: 12px;
            padding: 1rem;
        }
        
        /* ── Titles and Headers ── */
        h1, h2, h3 {
            background: linear-gradient(90deg, #f8fafc 0%, #94a3b8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 700 !important;
            letter-spacing: -0.5px;
        }
    </style>
    """, unsafe_allow_html=True)


def _render_top_bar() -> None:
    st.markdown("""
        <style>
        /* Hide Deploy Button and Header */
        header[data-testid="stHeader"] { display: none !important; }
        .stDeployButton { display: none !important; }
        
        /* Force vertical alignment across the top bar columns */
        div[data-testid='stHorizontalBlock'] { 
            align-items: center !important; 
        }
        
        /* Remove default Streamlit component margins in the top bar */
        div[data-testid='stHorizontalBlock'] .stCheckbox, 
        div[data-testid='stHorizontalBlock'] .stButton,
        div[data-testid='stHorizontalBlock'] div[data-testid="stMarkdownContainer"] p {
            margin-bottom: 0 !important;
            padding-bottom: 0 !important;
            display: flex;
            align-items: center;
        }
        
        div[data-testid='stHorizontalBlock'] div[data-testid="column"] {
            display: flex;
            align-items: center;
            justify-content: flex-start;
        }
        </style>
    """, unsafe_allow_html=True)
    cols = st.columns([2.5, 2.5, 1.5, 1.5, 1, 1])
    with cols[0]:
        st.markdown(
            "<div style='display:flex;align-items:center;gap:10px;'>"
            "<span style='font-size:1.5rem;'>🌍</span>"
            "<span style='font-size:1.1rem;font-weight:700;color:#ecf0f1;'>"
            f"{settings.APP_NAME}</span>"
            f"<span style='font-size:0.65rem;color:#95a5a6;background:rgba(52,152,219,0.15);"
            f"padding:2px 8px;border-radius:4px;'>v{settings.APP_VERSION}</span>"
            "</div>", unsafe_allow_html=True,
        )
    with cols[1]:
        st.markdown(
            f"<div style='color:#7f8c8d;font-size:0.75rem;padding-left:10px;'>"
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC</div>",
            unsafe_allow_html=True,
        )
    with cols[2]:
        auto = st.toggle("Live", value=st.session_state.get("auto_refresh", False), key="auto_refresh_toggle")
        st.session_state.auto_refresh = auto
    with cols[3]:
        if st.button("🔄 Refresh", width='stretch'):
            st.cache_data.clear()
            st.rerun()
    with cols[4]:
        st.markdown(
            "<div style='display:flex;align-items:center;gap:6px;'>"
            "<span class='pipeline-dot dot-healthy'></span>"
            "<span style='color:#10b981;font-size:0.75rem;font-weight:700;letter-spacing:0.5px;'>LIVE</span></div>",
            unsafe_allow_html=True,
        )
    with cols[5]:
        st.markdown(
            f"<div style='color:#7f8c8d;font-size:0.7rem;text-align:right;font-weight:600;'>"
            f"API: OK</div>", unsafe_allow_html=True,
        )


def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            "<div style='padding:8px 0;'>"
            "<span style='font-size:1.3rem;font-weight:700;color:#ecf0f1;'>🌍 GeoMarket</span>"
            "<span style='font-weight:300;color:#3498db;'>GPT</span>"
            "</div>", unsafe_allow_html=True,
        )
        st.caption("Intelligence Dashboard")

        st.divider()

        pages = {
            "Dashboard": "dashboard",
            "Scenario Simulation": "simulation",
            "Intelligence Reports": "report_generator",
            "AI Agent Console": "agent_console",
            "RAG Explorer": "rag_explorer",
        }
        icons = {
            "dashboard": "📊", "simulation": "🎲", "report_generator": "📋",
            "agent_console": "🤖", "rag_explorer": "🔍",
        }

        for label, page_key in pages.items():
            icon = icons.get(page_key, "📄")
            selected = st.session_state.get("page") == page_key
            if st.sidebar.button(
                f"{icon}  {label}",
                width='stretch',
                type="primary" if selected else "secondary",
                key=f"nav_{page_key}",
            ):
                st.session_state.page = page_key
                st.rerun()

        st.sidebar.divider()

        st.markdown("<div style='color:#7f8c8d;font-size:0.7rem;font-weight:600;margin-bottom:4px;'>FILTERS</div>", unsafe_allow_html=True)
        st.session_state.filter_severity = st.select_slider(
            "Min Severity", options=[0, 2, 4, 6, 8, 10], value=st.session_state.get("filter_severity", 0),
            label_visibility="collapsed",
        )
        st.session_state.filter_event_type = st.selectbox(
            "Event Type", ["All", "war", "sanctions", "election", "crisis",
                           "trade_dispute", "cyberattack", "natural_disaster", "civil_unrest"],
            index=0, label_visibility="collapsed",
        )
        st.session_state.filter_sector = st.multiselect(
            "Sectors", ["All", "energy", "defense", "technology", "finance",
                        "healthcare", "commodities", "utilities"],
            default=["All"], label_visibility="collapsed",
        )

        st.divider()
        st.markdown("<div style='color:#7f8c8d;font-size:0.7rem;font-weight:600;margin-bottom:4px;letter-spacing:1px;'>PIPELINE STATUS</div>", unsafe_allow_html=True)
        pipeline_statuses = [
            ("GDELT Ingest", "healthy", "20m cycle"),
            ("Reddit Feed", "healthy", "5m cycle"),
            ("Market Data", "running", "15m cycle"),
            ("RAG Index", "healthy", "updated"),
            ("Report Gen", "running", "20m cycle"),
            ("Prediction", "idle", "on demand"),
        ]
        for name, status, detail in pipeline_statuses:
            colors = {"healthy": "#10b981", "running": "#38bdf8", "idle": "#64748b"}
            color = colors.get(status, "#64748b")
            dot_class = f"dot-{status}"
            st.markdown(
                f"<div style='display:flex;align-items:center;justify-content:space-between;"
                f"padding:6px 10px;margin:3px 0;background:rgba(255,255,255,0.02);border-radius:6px;transition:background 0.2s ease;'>"
                f"<span style='color:#bdc3c7;font-size:0.75rem;display:flex;align-items:center;'>"
                f"<span class='pipeline-dot {dot_class}'></span>{name}</span>"
                f"<span style='color:{color};font-size:0.65rem;font-weight:700;letter-spacing:0.5px;'>{status.upper()}</span>"
                f"</div>", unsafe_allow_html=True,
            )

        st.divider()
        st.markdown(
            f"<div style='color:#4a5568;font-size:0.65rem;text-align:center;letter-spacing:0.5px;'>"
            f"© GeoMarketGPT • {datetime.now(timezone.utc).year}<br>"
            f"Data: GDELT • Reddit • Tiingo • Yahoo</div>",
            unsafe_allow_html=True,
        )


def main() -> None:
    inject_css()
    _render_top_bar()
    st.divider()

    _render_sidebar()

    if "page" not in st.session_state:
        st.session_state.page = "dashboard"

    routing = {
        "dashboard": _show_dashboard,
        "simulation": _show_simulation,
        "report_generator": _show_reports,
        "agent_console": _show_agents,
        "rag_explorer": _show_rag,
    }
    page_func = routing.get(st.session_state.page, _show_dashboard)
    page_func()

    if st.session_state.get("auto_refresh", False):
        time.sleep(30)
        st.rerun()


def _show_dashboard():
    from frontend.pages.dashboard import show
    show()


def _show_simulation():
    from frontend.pages.simulation import show
    show()


def _show_reports():
    from frontend.pages.report_generator import show
    show()


def _show_agents():
    from frontend.pages.agent_console import show
    show()


def _show_rag():
    from frontend.pages.rag_explorer import show
    show()


if __name__ == "__main__":
    main()
