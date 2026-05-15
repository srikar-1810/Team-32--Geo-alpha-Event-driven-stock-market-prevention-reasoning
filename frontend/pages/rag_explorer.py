from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import streamlit as st

from frontend.components.alerts import show_error, show_info, show_warning
from frontend.components.metrics import metric_card, section_header
from frontend.utils.api_client import api_client


def show() -> None:
    st.title("🔍 RAG Knowledge Explorer")
    st.caption("Retrieval-Augmented Generation over geopolitical and market data.")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input(
            "Ask a question about geopolitical events, market impacts, or historical patterns",
            placeholder="e.g., How did oil stocks perform during the 2022 Russia-Ukraine conflict?",
        )
    with col2:
        collection = st.selectbox(
            "Collection",
            ["geopol_events", "sentiment_data", "market_data", "reports", "all"],
        )

    top_k = st.slider("Number of results", 3, 20, 5)

    if query:
        with st.spinner("Querying knowledge base..."):
            try:
                result = asyncio.run(
                    api_client.query_rag(
                        query=query,
                        collection=collection if collection != "all" else "geopol_events",
                        top_k=top_k,
                    )
                )
            except Exception as e:
                show_error("RAG query failed", str(e))
                result = None

        if result:
            st.subheader("AI Response")
            st.markdown(result.get("answer", "No answer generated."))

            st.divider()
            st.subheader(f"Retrieved Context ({result.get('total_results', 0)} results)")

            col1, col2 = st.columns(2)
            with col1:
                metric_card("Results", str(result.get("total_results", 0)))
            with col2:
                metric_card(
                    "Processing Time",
                    f"{result.get('processing_time_ms', 0):.1f}ms",
                )

            for i, r in enumerate(result.get("results", []), 1):
                with st.expander(
                    f"[{i}] Score: {r.get('score', 0):.3f} | "
                    f"Collection: {r.get('collection', 'N/A')} | "
                    f"ID: {r.get('id', 'N/A')[:16]}..."
                ):
                    st.markdown(r.get("content", "No content"))
                    if r.get("metadata"):
                        st.caption("Metadata")
                        st.json(r["metadata"])

    else:
        show_info("Enter a question to search across the knowledge base.")

    st.divider()
    st.subheader("💡 Example Queries")
    examples = [
        "What geopolitical events are affecting the energy sector?",
        "Show me recent market data for the technology sector",
        "How did markets react to the last Fed rate decision?",
        "What is the current sentiment on AI stocks?",
        "Compare historical conflicts and their market impact",
    ]
    for ex in examples:
        if st.button(ex, width='stretch'):
            st.session_state["rag_query"] = ex
            st.rerun()
