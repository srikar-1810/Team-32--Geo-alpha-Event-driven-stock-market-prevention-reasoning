from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

from frontend.components.alerts import show_error, show_info, show_success, show_warning
from frontend.components.metrics import metric_card, section_header
from frontend.utils.api_client import api_client
from frontend.utils.helpers import format_timestamp, truncate


def _render_brief_item(b: Dict[str, Any]) -> None:
    with st.container(border=True):
        cols = st.columns([2, 1, 1, 1, 1, 1])
        cols[0].markdown(f"**{b.get('report_id', '?')[:12]}...**")
        cols[1].write(f"{b.get('generated_at', '?')[:16]}")
        cols[2].metric("Events", b.get("event_count", 0))
        cols[3].metric("Sectors", b.get("sector_count", 0))
        cols[4].metric("Severity", f"{b.get('severity_estimate', 0):.1f}")
        cols[5].metric("Conf.", f"{b.get('overall_confidence', 0):.0%}")

        with st.expander("Actions"):
            c1, c2, c3 = st.columns(3)
            rid = b.get("report_id", "")
            with c1:
                if st.button("📄 View Metadata", key=f"pdf_{rid}"):
                    try:
                        st.session_state[f"brief_json_{rid}"] = asyncio.run(api_client._request("GET", f"/api/v1/reports/brief/{rid}"))
                    except Exception as e:
                        show_error("Error", str(e))
            with c2:
                if st.button("📋 View Raw JSON", key=f"json_{rid}"):
                    try:
                        st.session_state[f"brief_json_{rid}"] = asyncio.run(api_client._request("GET", f"/api/v1/reports/brief/{rid}/json"))
                    except Exception as e:
                        show_error("Error", str(e))
            with c3:
                pdf_path = b.get("pdf_path", "")
                if pdf_path and Path(pdf_path).exists():
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            "⬇️ Download PDF",
                            data=f,
                            file_name=f"geopol_brief_{rid}.pdf",
                            mime="application/pdf",
                            key=f"dl_{rid}",
                        )
        
        if st.session_state.get(f"brief_json_{rid}"):
            st.json(st.session_state[f"brief_json_{rid}"])
            if st.button("Close Data", key=f"close_{rid}"):
                st.session_state[f"brief_json_{rid}"] = None
                st.rerun()


def show() -> None:
    st.title("📋 Intelligence Reports")
    st.caption("Autonomous AI-generated geopolitical intelligence briefings (every 20 minutes).")

    tab1, tab2, tab3 = st.tabs(["🔄 Auto Briefs", "📝 Generate", "📦 All Reports"])

    with tab1:
        st.subheader("Autonomous Intelligence Briefings")
        st.caption("Hedge-fund-quality briefings auto-generated every 20 minutes from GDELT, Reddit, market data, and RAG.")

        status_data = None
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("🔄 Refresh", width='stretch', key='refresh_reports'):
                st.rerun()
        with col2:
            if st.button("⚡ Trigger Now", type="primary", width='stretch'):
                with st.spinner("Generating brief..."):
                    try:
                        result = asyncio.run(
                            api_client._request("POST", "/api/v1/reports/brief/trigger")
                        )
                        st.success("Brief generated!")
                        st.rerun()
                    except Exception as e:
                        show_error("Trigger failed", str(e))
        with col3:
            if st.button("📊 Status", width='stretch'):
                try:
                    status_data = asyncio.run(
                        api_client._request("GET", "/api/v1/reports/brief/status")
                    )
                except Exception as e:
                    show_error("Status failed", str(e))
        with col4:
            pass

        if status_data:
            with st.expander("System Status JSON", expanded=True):
                st.json(status_data)

        st.divider()
        try:
            briefs_result = asyncio.run(
                api_client._request("GET", "/api/v1/reports/brief/list", params={"limit": 20})
            )
        except Exception as e:
            show_warning(f"Could not load briefs: {e}")
            briefs_result = {"items": []}

        items = briefs_result.get("items", [])
        if items:
            st.write(f"**{len(items)} brief(s) generated**")
            for b in items:
                _render_brief_item(b)
        else:
            show_info("No briefs generated yet. Click 'Trigger Now' to generate the first one.")

        st.divider()
        st.subheader("💡 About Auto Briefs")
        st.markdown("""
        Each intelligence briefing includes:
        - **Executive Summary** — AI-generated natural language synthesis of current geopolitical landscape
        - **Top Events** — Severity-ranked geopolitical events from GDELT (last 24h)
        - **Sector Impact Analysis** — Keyword-matched sector impacts with bar charts
        - **Stock Recommendations** — Bullish/bearish picks with relevance scoring
        - **Supply Chain Risks** — Critical node disruption assessment
        - **Historical Analogues** — Matched past events with market impact data
        - **Risk & Volatility** — 5-factor risk assessment + VIX regime gauge
        - **Outcome Scenarios** — Probability-weighted scenario analysis with visualizations
        - **PDF & JSON** — Downloadable institutional-grade reports
        """)

    with tab2:
        st.subheader("Manual Report Generation")
        with st.form("manual_report"):
            title = st.text_input("Report Title", "Custom Intelligence Brief")
            sections_text = st.text_area(
                "Sections (key: value per line)",
                placeholder="executive_summary: The geopolitical landscape shows...\nsector_analysis: Energy sector under pressure...",
                height=150,
            )
            fmt = st.selectbox("Format", ["markdown", "html", "json"])
            if st.form_submit_button("Generate Report"):
                sections = {}
                for line in sections_text.strip().split("\n"):
                    if ":" in line:
                        k, v = line.split(":", 1)
                        sections[k.strip()] = v.strip()
                with st.spinner("Generating..."):
                    try:
                        result = asyncio.run(
                            api_client._request(
                                "POST", "/api/v1/reports/generate",
                                json={"title": title, "sections": sections, "format": fmt},
                            )
                        )
                        st.success("Report generated!")
                        st.json(result)
                    except Exception as e:
                        show_error("Generation failed", str(e))

    with tab3:
        st.subheader("All Reports")
        try:
            reports = asyncio.run(
                api_client._request("GET", "/api/v1/reports", params={"page": 1, "page_size": 50})
            )
            items = reports.get("items", [])
            if items:
                for r in items:
                    with st.container(border=True):
                        cols = st.columns([3, 1, 1, 1])
                        cols[0].write(f"**{r.get('title', '?')}**")
                        cols[1].write(r.get("format", "").upper())
                        cols[2].write(r.get("status", "").upper())
                        cols[3].write(format_timestamp(r.get("created_at")))
            else:
                show_info("No reports found.")
        except Exception as e:
            show_warning(f"Could not load reports: {e}")


if __name__ == "__main__":
    show()
