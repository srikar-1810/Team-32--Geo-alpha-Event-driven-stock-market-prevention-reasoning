"""Main dashboard — Bloomberg/Palantir-style institutional intelligence hub."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import streamlit as st

from frontend.components.alerts import show_error, show_info, show_success, show_warning
from frontend.components.charts import (
    confidence_gauge,
    outcome_pie,
    return_comparison_bars,
    sector_heatmap,
    sector_impact_bars,
    sentiment_timeline,
    signal_contribution_waterfall,
    volatility_gauge,
)
from frontend.components.metrics import (
    ai_reasoning_panel,
    confidence_meter,
    event_card,
    metric_card,
    pipeline_status_card,
    section_header,
    stock_card,
)
from frontend.utils.api_client import api_client
from frontend.utils.helpers import format_timestamp, truncate


def show() -> None:
    severity_filter = st.session_state.get("filter_severity", 0)
    event_type_filter = st.session_state.get("filter_event_type", "All")
    sector_filter = st.session_state.get("filter_sector", ["All"])

    events_data = _fetch_data("events", severity_filter, event_type_filter)
    sentiment_data = _fetch_data("sentiment")
    market_data = _fetch_data("market")
    pipeline_data = _fetch_data("pipeline")
    brief_data = _fetch_data("brief")

    events = events_data or []
    sentiment = sentiment_data or {}
    market = market_data or {}
    pipeline = pipeline_data or {}
    brief = brief_data or {}

    num_events = len(events)
    avg_severity = sum(e.get("severity", e.get("severity_estimate", 5)) for e in events[:5]) / max(num_events, 1) if events else 0
    sectors_impacted = _count_sectors(events)

    overall_conf = brief.get("overall_confidence", 0) if brief else 0
    vix_est = brief.get("volatility_outlook", {}).get("estimated_vol_expansion", 15) if brief else 15

    section_header("Market Intelligence Overview",
                   f"{num_events} events • {avg_severity:.1f}/10 avg severity • {sectors_impacted} sectors affected")

    cols = st.columns(5)
    with cols[0]:
        metric_card("Events Tracked", str(num_events), color="blue")
    with cols[1]:
        metric_card("Avg Severity", f"{avg_severity:.1f}/10",
                     delta=f"{'▲' if avg_severity > 5 else '▼'} {abs(avg_severity - 5):.1f}", color="gold")
    with cols[2]:
        metric_card("Sectors Active", str(sectors_impacted), color="green")
    with cols[3]:
        metric_card("Confidence", f"{overall_conf:.0%}", color="blue" if overall_conf > 0.5 else "gold")
    with cols[4]:
        regime = brief.get("volatility_outlook", {}).get("expected_regime", "normal") if brief else "normal"
        vix_color = "red" if vix_est > 25 else "gold" if vix_est > 15 else "green"
        metric_card(f"VIX Est ({regime.upper()})", f"{vix_est:.0f}", color=vix_color)

    st.divider()

    col_left, col_right = st.columns([1.4, 1])
    with col_left:
        section_header("Live Geopolitical Event Feed", "Top events from GDELT (24h)")
        if events:
            for evt in events[:6]:
                st.markdown(event_card(evt), unsafe_allow_html=True)
        else:
            st.info("No events match current filters.")

    with col_right:
        section_header("Quick Actions")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🚀 Trigger Brief", width='stretch'):
                try:
                    result = asyncio.run(api_client._request("POST", "/api/v1/reports/brief/trigger"))
                    st.success(f"Brief: {result.get('brief', {}).get('report_id', 'done')}")
                except Exception as e:
                    show_error("Brief trigger", str(e))
        with c2:
            if st.button("🎲 Run Simulation", width='stretch'):
                st.session_state.page = "simulation"
                st.rerun()

        st.divider()
        section_header("System Health")
        if pipeline_data:
            metric_card("API Status", "Healthy", color="blue")
        else:
            metric_card("API Status", "Connecting...", color="gold")


    st.divider()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏭 Sectors", "📈 Stocks", "🧠 AI Analysis", "📜 History", "🎯 Scenarios"])

    with tab1:
        col1, col2 = st.columns([1, 1])
        with col1:
            section_header("Sector Impact Matrix")
            sectors = brief.get("sectors", _build_fallback_sectors(events)) if brief else _build_fallback_sectors(events)
            if sectors:
                sector_heatmap(sectors)
            else:
                st.info("No sector data.")
        with col2:
            section_header("Sector Magnitudes")
            if sectors:
                sector_impact_bars(sectors)
            else:
                st.info("No sector data.")

    with tab2:
        col1, col2 = st.columns([1, 1])
        with col1:
            section_header("🟢 Bullish Picks")
            bullish = brief.get("top_bullish", []) if brief else []
            if bullish:
                for s in bullish[:5]:
                    st.markdown(stock_card(
                        s.get("ticker", ""), s.get("company", ""),
                        "bullish", s.get("relevance", 0.5),
                        s.get("sector", ""), s.get("reasoning", ""),
                    ), unsafe_allow_html=True)
            else:
                st.info("No bullish picks in current cycle.")
        with col2:
            section_header("🔴 Bearish Picks")
            bearish = brief.get("top_bearish", []) if brief else []
            if bearish:
                for s in bearish[:5]:
                    st.markdown(stock_card(
                        s.get("ticker", ""), s.get("company", ""),
                        "bearish", s.get("relevance", 0.5),
                        s.get("sector", ""), s.get("reasoning", ""),
                    ), unsafe_allow_html=True)
            else:
                st.info("No bearish picks in current cycle.")

    with tab3:
        col1, col2 = st.columns([1.5, 1])
        with col1:
            exec_summary = brief.get("executive_summary", brief.get("report", {}).get("executive_summary", "")) if brief else ""
            if exec_summary:
                ai_reasoning_panel(
                    "Executive Intelligence Summary",
                    exec_summary,
                    key_drivers=[s.get("sector_name", "") for s in (brief.get("sectors", []) if brief else [])[:4]],
                    confidence=overall_conf,
                )
            else:
                st.info("Run a brief or simulation to generate AI analysis.")

            kj = brief.get("key_judgments", brief.get("report", {}).get("key_judgments", [])) if brief else []
            if kj:
                section_header("Key Judgments")
                for j in kj[:3]:
                    st.markdown(
                        f"<div style='background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);"
                        f"border-radius:6px;padding:10px 14px;margin:4px 0;'>"
                        f"<div style='color:#ecf0f1;font-size:0.85rem;font-weight:500;'>"
                        f"{j.get('judgment', '')}</div>"
                        f"<div style='color:#7f8c8d;font-size:0.75rem;margin-top:4px;'>"
                        f"Confidence: {j.get('confidence', 0):.0%} — {j.get('detail', '')}</div>"
                        f"</div>", unsafe_allow_html=True,
                    )
        with col2:
            section_header("Confidence Decomposition")
            signals = {"news": 0, "social": 0, "historical": 0, "momentum": 0, "volatility": 0}
            if brief:
                recs = brief.get("report", {}).get("recommendations", [])
                if recs:
                    for i, r in enumerate(recs[:5]):
                        signals[list(signals.keys())[i % 5]] = 0.2 * (5 - i) * 0.3
            confidence_gauge(overall_conf, "Overall Confidence")

            section_header("Volatility Regime")
            if brief:
                vol = brief.get("volatility_outlook", {})
                volatility_gauge(vol.get("estimated_vol_expansion", 15), vol.get("expected_regime", "normal"))

    with tab4:
        col1, col2 = st.columns([1, 1])
        with col1:
            section_header("Historical Analogues")
            analogies = brief.get("analogies", []) if brief else []
            if analogies:
                for a in analogies[:4]:
                    st.markdown(
                        f"<div style='background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);"
                        f"border-radius:6px;padding:10px 14px;margin:4px 0;'>"
                        f"<div style='display:flex;justify-content:space-between;'>"
                        f"<span style='color:#ecf0f1;font-weight:600;font-size:0.85rem;'>{a.get('event_title', '')}</span>"
                        f"<span style='color:#3498db;font-size:0.75rem;'>{a.get('similarity_score', 0):.0%} match</span>"
                        f"</div>"
                        f"<div style='display:flex;gap:16px;margin-top:6px;font-size:0.75rem;color:#7f8c8d;'>"
                        f"<span>SPY 5d: {a.get('return_5d', 0):+.1f}%</span>"
                        f"<span>SPY 30d: {a.get('return_30d', 0):+.1f}%</span>"
                        f"<span>VIX Δ: {a.get('volatility_change', 0):+.1f}</span>"
                        f"</div>"
                        f"<div style='font-size:0.75rem;color:#95a5a6;margin-top:4px;'>{a.get('event_date', '')}</div>"
                        f"</div>", unsafe_allow_html=True,
                    )
            else:
                st.info("No historical analogues in current cycle.")
        with col2:
            section_header("Similarity Returns", "5d and 30d returns for matched analogues")
            analogies = brief.get("analogies", []) if brief else []
            if analogies:
                items = [
                    {"label": a.get("event_title", "")[:16], "return_5d": a.get("return_5d", 0), "return_30d": a.get("return_30d", 0)}
                    for a in analogies[:6]
                ]
                return_comparison_bars(items)
            else:
                st.info("Run analysis to see historical return comparisons.")

    with tab5:
        col1, col2 = st.columns([1, 1])
        with col1:
            section_header("Outcome Scenarios")
            outcomes = brief.get("outcomes", []) if brief else []
            if outcomes:
                outcome_pie(outcomes)
            else:
                st.info("No outcome scenarios.")
        with col2:
            section_header("Scenario Details")
            outcomes = brief.get("outcomes", []) if brief else []
            if outcomes:
                for o in sorted(outcomes, key=lambda x: x.get("probability", 0), reverse=True):
                    direction = o.get("direction", "neutral")
                    emoji = {"bullish": "🟢", "bearish": "🔴", "mixed": "🟡", "neutral": "⚪"}.get(direction, "⚪")
                    st.markdown(
                        f"<div style='background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);"
                        f"border-radius:6px;padding:10px 14px;margin:4px 0;'>"
                        f"<div style='display:flex;justify-content:space-between;'>"
                        f"<span style='color:#ecf0f1;font-size:0.85rem;font-weight:500;'>{emoji} {o.get('scenario_label', '')[:35]}</span>"
                        f"<span style='color:#3498db;font-weight:600;'>{o.get('probability', 0):.0%}</span>"
                        f"</div>"
                        f"<div style='font-size:0.75rem;color:#95a5a6;margin-top:4px;'>{o.get('narrative', '')[:120]}...</div>"
                        f"<div style='font-size:0.7rem;color:#7f8c8d;margin-top:4px;'>"
                        f"5d: {o.get('market_return_5d', 0):+.1f}% | 30d: {o.get('market_return_30d', 0):+.1f}%</div>"
                        f"</div>", unsafe_allow_html=True,
                    )

    st.divider()
    section_header("Scenario Simulation", "Quick what-if analysis")
    sim_query = st.text_input("Describe a hypothetical scenario", placeholder="e.g., What if OPEC cuts production by 2 million barrels?", label_visibility="collapsed")
    if st.button("Run Simulation", type="primary", width='stretch', disabled=not sim_query):
        st.session_state.sim_query = sim_query
        st.session_state.page = "simulation"
        st.rerun()

    st.divider()
    section_header("Download Reports")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("📄 Latest PDF Brief", width='stretch'):
            try:
                brief_data = asyncio.run(api_client._request("GET", "/api/v1/reports/brief/latest"))
                pdf_path = brief_data.get("metadata", {}).get("pdf_path", "")
                if pdf_path:
                    import base64
                    with open(pdf_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode()
                        href = f'<a href="data:application/pdf;base64,{b64}" download="geopol_brief.pdf">Click to download</a>'
                        st.markdown(href, unsafe_allow_html=True)
                else:
                    st.info("No PDF available yet.")
            except Exception as e:
                show_error("Download", str(e))
    with c2:
        if st.button("📋 Latest JSON Data", width='stretch'):
            try:
                brief_data = asyncio.run(api_client._request("GET", "/api/v1/reports/brief/latest"))
                st.json(brief_data.get("data", brief_data))
            except Exception as e:
                show_error("Download JSON", str(e))
    with c3:
        if st.button("⚡ Trigger New Brief", width='stretch'):
            try:
                result = asyncio.run(api_client._request("POST", "/api/v1/reports/brief/trigger"))
                st.success(f"Brief triggered: {result.get('brief', {}).get('report_id', '')}")
            except Exception as e:
                show_error("Trigger", str(e))


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_data(data_type: str, severity: int = 0, event_type: str = "All") -> Any:
    try:
        if data_type == "events":
            result = asyncio.run(api_client.get_geopol_events(
                hours=24, limit=15, min_severity=severity / 10.0,
            ))
            items = result.get("items", result.get("events", result.get("data", [])))
            if event_type != "All":
                items = [e for e in items if e.get("event_type", "").lower() == event_type.lower()]
            return items
        elif data_type == "sentiment":
            return asyncio.run(api_client.get_sentiment_trends(hours=24))
        elif data_type == "market":
            return asyncio.run(api_client.get_market_data("SPY", "2024-01-01", "2024-12-31"))
        elif data_type == "pipeline":
            try:
                return asyncio.run(api_client.health_check())
            except Exception:
                return {}
        elif data_type == "brief":
            try:
                return asyncio.run(api_client._request("GET", "/api/v1/reports/brief/latest"))
            except Exception:
                return {}
    except Exception as e:
        return None


def _count_sectors(events: List[Dict]) -> int:
    all_sectors = set()
    for e in events:
        for s in e.get("affected_sectors", e.get("sectors_impacted", [])):
            if isinstance(s, dict):
                all_sectors.add(s.get("sector_name", s.get("name", "")))
            elif isinstance(s, str):
                all_sectors.add(s)
    return len(all_sectors) or 0


def _build_fallback_sectors(events: List[Dict]) -> List[Dict]:
    SECTOR_ETF_MAP = {
        "SPY": "S&P 500", "QQQ": "NASDAQ-100", "IWM": "Russell 2000", "EEM": "Emerging Markets",
        "XLF": "Financials", "XLE": "Energy", "XLK": "Technology", "XLV": "Healthcare",
        "XLI": "Industrials", "XLB": "Materials", "XLU": "Utilities", "XLY": "Consumer Cyclical",
        "XLP": "Consumer Defensive", "XLRE": "Real Estate", "XLC": "Communication Services",
        "VNQ": "Real Estate", "GLD": "Gold", "SLV": "Silver", "USO": "Oil",
        "TLT": "Long-Term Treasury", "SHY": "Short-Term Treasury", "AGG": "Aggregate Bond",
        "LQD": "Corporate Bond", "HYG": "High-Yield Bond",
        "VIX": "Volatility Index",
    }
    sectors = []
    text = " ".join(f"{e.get('title', '')} {e.get('description', '')} {e.get('event_type', '')}".lower() for e in events)
    for etf, name in SECTOR_ETF_MAP.items():
        if name.split()[0].lower() in text:
            sectors.append({
                "sector_name": name, "etf_ticker": etf,
                "impact_direction": "bullish",
                "impact_magnitude": 0.5,
                "confidence": 0.5,
                "reasoning": "Keyword-matched sector exposure",
            })
    return sectors[:8]
