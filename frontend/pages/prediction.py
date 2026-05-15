from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import streamlit as st

from frontend.components.alerts import show_error, show_info, show_success, show_warning
from frontend.components.charts import plot_bar_chart, plot_impact_heatmap
from frontend.components.metrics import metric_card, section_header
from frontend.utils.api_client import api_client
from frontend.utils.helpers import format_percentage, format_timestamp


def _render_sector_prediction(sp: Dict) -> None:
    direction = sp.get("direction", "neutral")
    emoji = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪", "mixed": "🟡"}.get(direction, "⚪")
    with st.container(border=True):
        cols = st.columns([2, 1, 1, 1, 1])
        cols[0].markdown(f"{emoji} **{sp.get('sector_name', '')}** ({sp.get('etf_ticker', '')})")
        cols[1].metric("Direction", direction.upper())
        cols[2].metric("5d", f"{sp.get('predicted_return_5d', 0):+.1f}%")
        cols[3].metric("30d", f"{sp.get('predicted_return_30d', 0):+.1f}%")
        cols[4].metric("Confidence", f"{sp.get('confidence', 0):.0%}")
        st.caption(sp.get("reasoning", {}).get("short_summary", ""))
        with st.expander("Details"):
            reasoning = sp.get("reasoning", {})
            st.markdown(f"**Key drivers:** {', '.join(reasoning.get('key_drivers', []))}")
            st.markdown(f"**Risk factors:** {', '.join(reasoning.get('risk_factors', []))}")
            st.markdown(f"**Detailed reasoning:** {reasoning.get('detailed_reasoning', '')}")

            contribs = sp.get("contributions", {})
            if contribs:
                st.divider()
                st.markdown("**Signal Contributions**")
                for signal_key, signal_name in [
                    ("news_signal", "News"), ("social_signal", "Social"),
                    ("historical_signal", "Historical"), ("momentum_signal", "Momentum"),
                    ("volatility_signal", "Volatility"),
                ]:
                    sig = contribs.get(signal_key, {})
                    if sig:
                        score = sig.get("contribution_score", 0)
                        bar = "█" * max(0, int(abs(score) * 10)) + "░" * max(0, 10 - int(abs(score) * 10))
                        st.markdown(f"  {signal_name}: `{bar}` {score:+.3f} (w={sig.get('weight', 0):.2f})")


def _render_stock_prediction(sp: Dict) -> None:
    direction = sp.get("direction", "neutral")
    emoji = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}.get(direction, "⚪")
    with st.container(border=True):
        cols = st.columns([2, 1, 1, 1, 1])
        cols[0].markdown(f"{emoji} **{sp.get('ticker', '')}** ({sp.get('company_name', '')})")
        cols[1].metric("Direction", direction.upper())
        cols[2].metric("5d", f"{sp.get('predicted_return_5d', 0):+.1f}%")
        cols[3].metric("30d", f"{sp.get('predicted_return_30d', 0):+.1f}%")
        cols[4].metric("Confidence", f"{sp.get('confidence', 0):.0%}")
        st.caption(sp.get("reasoning", {}).get("short_summary", ""))
        price_targets = sp.get("price_targets", {})
        if price_targets:
            st.caption(f"Targets: {', '.join(f'{k}={v:.1f}' for k, v in price_targets.items())}")


def show() -> None:
    st.title("🔮 Market Prediction & Explainability")
    st.caption("AI-powered market predictions with full signal decomposition and reasoning.")

    query = st.text_area(
        "Describe the event or market condition",
        placeholder="What will happen to energy stocks if OPEC cuts production?",
        height=80,
    )

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        ticker_input = st.text_input(
            "Tickers (comma-separated, optional)",
            placeholder="SPY, XLE, GLD, AAPL",
        )
    with col2:
        sector_input = st.multiselect(
            "Sectors (optional)",
            ["energy", "technology", "finance", "healthcare", "defense",
             "materials", "utilities", "consumer", "real_estate", "communication"],
        )
    with col3:
        location = st.text_input("Location (optional)", placeholder="Ukraine, Middle East")

    if st.button("🔮 Generate Prediction", type="primary", disabled=not query):
        tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()] if ticker_input else None

        with st.spinner("Generating prediction with full explainability..."):
            try:
                result = asyncio.run(api_client.generate_prediction(
                    query=query,
                    tickers=tickers,
                    sectors=sector_input if sector_input else None,
                    location=location,
                ))
            except Exception as e:
                show_error("Prediction failed", str(e))
                return

        st.success(f"Prediction generated in {result.get('execution_time_ms', 0):.0f}ms")
        st.metric("Overall Confidence", f"{result.get('overall_confidence', 0):.0%}")

        sector_preds = result.get("sector_predictions", [])
        stock_preds = result.get("stock_predictions", [])
        top_bullish = result.get("top_bullish", [])
        top_bearish = result.get("top_bearish", [])
        high_vol = result.get("high_volatility_warnings", [])

        if sector_preds:
            st.divider()
            st.subheader("🏭 Sector Predictions")
            names = [s.get("sector_name", "")[:12] for s in sector_preds]
            returns = [s.get("predicted_return_5d", 0) for s in sector_preds]
            colors = ["#2ecc71" if r > 0 else "#e74c3c" if r < 0 else "#95a5a6" for r in returns]
            plot_bar_chart(names, returns, "Predicted 5d Return (%)", colors=colors)

            for sp in sector_preds:
                _render_sector_prediction(sp)

        if stock_preds:
            st.divider()
            st.subheader("📊 Stock Predictions")
            for sp in stock_preds[:10]:
                _render_stock_prediction(sp)

        if top_bullish:
            st.divider()
            st.subheader("🟢 Top Bullish Signals")
            for s in top_bullish[:5]:
                st.markdown(f"- **{s.get('ticker', '')}**: direction={s.get('direction', '')}, confidence={s.get('confidence', 0):.0%}")

        if top_bearish:
            st.divider()
            st.subheader("🔴 Top Bearish Signals")
            for s in top_bearish[:5]:
                st.markdown(f"- **{s.get('ticker', '')}**: direction={s.get('direction', '')}, confidence={s.get('confidence', 0):.0%}")

        if high_vol:
            st.divider()
            st.subheader("⚠️ High Volatility Warnings")
            for s in high_vol:
                st.warning(f"**{s.get('ticker', '')}**: {s.get('warning', '')}")

    st.divider()
    st.subheader("💡 Explainability Example")
    if st.button("Try it: Explain AAPL"):
        with st.spinner("Fetching explainability..."):
            try:
                explanation = asyncio.run(api_client.explain_prediction(
                    ticker="AAPL",
                    query="How will AAPL perform given current geopolitical tensions?",
                ))
                st.json(explanation)
            except Exception as e:
                show_error("Explainability failed", str(e))


if __name__ == "__main__":
    show()
