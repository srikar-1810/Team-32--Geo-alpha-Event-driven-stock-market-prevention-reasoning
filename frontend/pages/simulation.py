from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import streamlit as st

from frontend.components.alerts import show_error, show_info, show_success, show_warning
from frontend.components.charts import plot_bar_chart, plot_impact_heatmap
from frontend.components.metrics import metric_card, section_header
from frontend.utils.api_client import api_client
from frontend.utils.helpers import format_timestamp, truncate


def _render_supply_chain(impacts: List[Dict]) -> None:
    if not impacts:
        st.caption("No significant supply chain impacts identified.")
        return
    for sc in impacts:
        color = {
            "critical": "🔴", "severe": "🟠", "moderate": "🟡", "minor": "🟢",
        }.get(sc.get("impact_severity", ""), "⚪")
        with st.expander(f"{color} {sc.get('node', 'Unknown')} ({sc.get('impact_severity', '').upper()})"):
            st.write(sc.get("description", ""))
            if sc.get("affected_companies"):
                st.caption(f"Companies: {', '.join(sc['affected_companies'][:5])}")
            st.caption(f"Est. disruption: {sc.get('estimated_disruption_days', 0)} days | Confidence: {sc.get('confidence', 0):.0%}")


def _render_analogies(analogies: List[Dict]) -> None:
    if not analogies:
        st.caption("No close historical analogues identified.")
        return
    for a in analogies:
        with st.expander(f"{a.get('event_title', 'Unknown')} ({a.get('event_date', '')}) — {a.get('similarity_score', 0):.0%} match"):
            sims = a.get("key_similarities", [])
            diffs = a.get("key_differences", [])
            if sims:
                st.markdown("**Similarities:** " + ", ".join(sims[:3]))
            if diffs:
                st.markdown("**Differences:** " + ", ".join(diffs[:3]))
            cols = st.columns(3)
            cols[0].metric("SPY 5d", f"{a.get('return_5d', 0):+.1f}%")
            cols[1].metric("SPY 30d", f"{a.get('return_30d', 0):+.1f}%")
            cols[2].metric("VIX Δ", f"{a.get('volatility_change', 0):+.1f}")


def _render_outcomes(outcomes: List[Dict]) -> None:
    if not outcomes:
        return
    st.subheader("Outcome Scenarios")
    for o in sorted(outcomes, key=lambda x: x.get("probability", 0), reverse=True):
        direction = o.get("direction", "neutral")
        emoji = {"bullish": "📈", "bearish": "📉", "neutral": "➡️", "mixed": "🔀"}.get(direction, "❓")
        with st.container(border=True):
            cols = st.columns([2, 1, 1, 1])
            cols[0].markdown(f"{emoji} **{o.get('scenario_label', '')}**")
            cols[1].metric("Prob", f"{o.get('probability', 0):.0%}")
            cols[2].metric("5d", f"{o.get('market_return_5d', 0):+.1f}%")
            cols[3].metric("30d", f"{o.get('market_return_30d', 0):+.1f}%")
            st.caption(o.get("narrative", "")[:200])
            if o.get("key_catalysts"):
                st.caption("Catalysts: " + ", ".join(o["key_catalysts"][:3]))


def _render_risk(risk_factors: List[Dict], volatility: Dict) -> None:
    if risk_factors:
        st.subheader("Risk Factors")
        for rf in sorted(risk_factors, key=lambda r: r.get("severity", 0), reverse=True):
            sev = rf.get("severity", 0)
            bar = "█" * int(sev * 10) + "░" * (10 - int(sev * 10))
            with st.container(border=True):
                st.markdown(f"**{rf.get('risk_factor', '')}**  `{bar}` {sev:.2f}")
                st.caption(f"Probability: {rf.get('probability', 0):.0%}")
                st.caption(rf.get("impact_description", ""))
    if volatility:
        st.subheader("Volatility Outlook")
        cols = st.columns(3)
        cols[0].metric("Regime", volatility.get("expected_regime", "").upper())
        cols[1].metric("VIX Est.", f"{volatility.get('estimated_vol_expansion', 0):.0f}")
        cols[2].metric("Tail Risk", volatility.get("tail_risk_assessment", "")[:30])


def _render_report(report: Dict) -> None:
    if not report:
        return
    with st.expander("📋 Full Intelligence Report", expanded=False):
        st.markdown(f"### {report.get('title', 'Report')}")
        st.markdown(report.get("executive_summary", ""))
        st.divider()
        st.markdown("**Key Judgments**")
        for kj in report.get("key_judgments", []):
            st.markdown(f"- {kj.get('judgment', '')} (conf: {kj.get('confidence', 0):.0%})")
            st.caption(kj.get("detail", ""))
        st.divider()
        st.markdown("**Recommendations**")
        for r in report.get("recommendations", []):
            st.markdown(f"- {r}")
        st.divider()
        st.caption("Confidence: " + report.get("confidence_assessment", ""))
        for d in report.get("disclaimers", []):
            st.caption(f"⚠️ {d}")


def show() -> None:
    st.title("🎲 What-If Scenario Simulation")
    st.caption("AI-powered geopolitical scenario analysis with market impact prediction.")

    query = st.text_area(
        "Describe your hypothetical scenario",
        placeholder="What if China imposes sanctions on Taiwan? What if a major earthquake hits California? What if OPEC collapses?",
        height=100,
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        run = st.button("🚀 Run Simulation", type="primary", disabled=not query)
    with col2:
        st.caption("The AI will parse your scenario, identify affected sectors/stocks, assess supply chain impact, find historical analogues, and generate a structured report.")

    examples = [
        "What if Russia launches a cyberattack on US power grids?",
        "What if the EU imposes a total embargo on Russian energy exports?",
        "What if a major earthquake disrupts semiconductor production in Taiwan?",
        "What if the US defaults on its debt?",
        "What if North Korea successfully tests an ICBM?",
    ]
    if not query:
        st.caption("Try one of these examples:")
        for ex in examples:
            if st.button(ex, width='stretch'):
                query = ex
                st.rerun()

    if run:
        with st.spinner("Running full simulation pipeline..."):
            try:
                result = asyncio.run(api_client.run_simulation(query))
            except Exception as e:
                show_error("Simulation failed", str(e))
                return

        st.success(f"Simulation complete in {result.get('execution_time_ms', 0):.0f}ms")
        scenario = result.get("parsed_scenario", {})
        sectors = result.get("sectors", [])
        stocks = result.get("stocks", [])
        supply_chain = result.get("supply_chain_impacts", [])
        analogies = result.get("analogies", [])
        outcomes = result.get("outcomes", [])
        risk_factors = result.get("risk_factors", [])
        volatility = result.get("volatility_outlook", {})
        report = result.get("report", {})
        top_bullish = result.get("top_bullish", [])
        top_bearish = result.get("top_bearish", [])

        st.subheader("Scenario Overview")
        cols = st.columns(5)
        cols[0].metric("Event Type", scenario.get("event_type", "?"))
        cols[1].metric("Severity", f"{scenario.get('severity_estimate', 0):.1f}/10")
        cols[2].metric("Scope", scenario.get("economic_scope", "?").upper())
        cols[3].metric("Timeline", scenario.get("estimated_timeline", "?").replace("_", " "))
        cols[4].metric("Confidence", f"{result.get('overall_confidence', 0):.0%}")
        if scenario.get("countries"):
            st.caption(f"Countries: {', '.join(scenario['countries'])}")
        if scenario.get("actors"):
            st.caption(f"Key actors: {', '.join(scenario['actors'])}")
        if scenario.get("uncertainty_factors"):
            st.caption(f"Uncertainty: {', '.join(scenario['uncertainty_factors'][:3])}")

        st.divider()
        tab_sectors, tab_stocks, tab_supply, tab_history, tab_risk, tab_outcomes, tab_report = st.tabs([
            "🏭 Sectors", "📊 Stocks", "🔗 Supply Chain",
            "📜 History", "⚠️ Risk", "🎯 Outcomes", "📋 Report",
        ])

        with tab_sectors:
            if sectors:
                names = [s.get("sector_name", "") for s in sectors]
                mags = [s.get("impact_magnitude", 0) for s in sectors]
                colors = [
                    "#2ecc71" if s.get("impact_direction") == "bullish"
                    else "#e74c3c" if s.get("impact_direction") == "bearish"
                    else "#95a5a6"
                    for s in sectors
                ]
                plot_bar_chart(names, mags, "Sector Impact Magnitude", colors=colors)
                for s in sectors:
                    emoji = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}.get(s.get("impact_direction", ""), "⚪")
                    st.markdown(f"{emoji} **{s['sector_name']}** ({s.get('etf_ticker', '')}): {s.get('impact_magnitude', 0):.2f} — {s.get('reasoning', '')}")
            else:
                st.info("No sector impacts inferred.")

        with tab_stocks:
            if top_bullish:
                st.markdown("**🟢 Top Bullish Picks**")
                for s in top_bullish[:5]:
                    st.markdown(f"- **{s.get('ticker', '')}** ({s.get('sector', '')}): relevance={s.get('relevance', 0):.2f}")
                    st.caption(s.get("reasoning", ""))
            if top_bearish:
                st.markdown("**🔴 Top Bearish Picks**")
                for s in top_bearish[:5]:
                    st.markdown(f"- **{s.get('ticker', '')}** ({s.get('sector', '')}): relevance={s.get('relevance', 0):.2f}")
                    st.caption(s.get("reasoning", ""))

        with tab_supply:
            _render_supply_chain(supply_chain)

        with tab_history:
            _render_analogies(analogies)

        with tab_risk:
            _render_risk(risk_factors, volatility)

        with tab_outcomes:
            _render_outcomes(outcomes)

        with tab_report:
            _render_report(report)


if __name__ == "__main__":
    show()
