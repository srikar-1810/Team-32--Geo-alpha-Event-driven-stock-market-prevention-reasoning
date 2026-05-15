from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from app.services.workflow.base import EnhancedAgentNode
from app.services.workflow.prompts import HISTORICAL_RAG_SYSTEM
from app.services.workflow.state import WorkflowState
from app.services.workflow.tools import AgentTools


class HistoricalAnalystNode(EnhancedAgentNode):
    """Agent node: retrieves historical analogues from the RAG system."""

    def __init__(self, tools: Optional[AgentTools] = None) -> None:
        super().__init__(
            agent_id="historical-analyst",
            agent_name="Historical RAG Analyst Agent",
        )
        self._tools_inst = tools or AgentTools()

    def _goals(self) -> str:
        return (
            "Retrieve similar historical geopolitical events from the vector database. "
            "Identify analogues, recognize patterns in market reactions, "
            "detect anomalies, and assess how similar situations unfolded "
            "across sectors and asset classes."
        )

    async def __call__(self, state: WorkflowState) -> WorkflowState:
        start = time.perf_counter()
        self._log_step(state, "START")

        query = state.get("query", "")
        tickers = state.get("tickers", [])
        news_analysis = state.get("news_analysis", {}) or {}
        sectors_from_news = [
            s.get("sector", "") for s in (news_analysis.get("primary_sectors_impacted") or [])
        ]

        search_queries = [query]
        if tickers:
            search_queries.append(f"{' '.join(tickers[:3])} {query}")
        if sectors_from_news:
            search_queries.append(f"{' '.join(sectors_from_news[:3])} geopolitical event")

        all_rag_results: List[Dict[str, Any]] = []
        for sq in search_queries[:3]:
            rag_data = await self._tools_inst.query_historical_rag(sq, top_k=8)
            all_rag_results.extend(rag_data.get("results", []))

        seen_ids: set = set()
        unique_results: list = []
        for r in all_rag_results:
            eid = r.get("event_id", "")
            if eid and eid not in seen_ids:
                seen_ids.add(eid)
                unique_results.append(r)

        unique_results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        top_analogues = unique_results[:10]

        market_reactions = {}
        if top_analogues:
            rag_full = await self._tools_inst.query_historical_rag(query, top_k=15)
            market_reactions = rag_full.get("market_reactions", {})

        state["historical_analogues"] = top_analogues

        analogues_text = self._format_analogues(top_analogues)

        context = self._build_context(state)
        sector_str = ", ".join(sectors_from_news) if sectors_from_news else "various"

        user_prompt = (
            f"Analyze historical analogues for this geopolitical event.\n\n"
            f"Current event: {query}\n"
            f"Tickers: {', '.join(tickers)}\n"
            f"News-indicated sectors: {sector_str}\n\n"
            f"Top historical analogues ({len(top_analogues)} found):\n{analogues_text}\n\n"
            f"Aggregated market reactions from similar events:\n"
            f"  Avg Volatility Change: {market_reactions.get('avg_volatility_change_pct', 'N/A')}%\n"
            f"  Avg Market 5d Return: {market_reactions.get('avg_market_return_5d', 'N/A')}%\n"
            f"  Avg Market 30d Return: {market_reactions.get('avg_market_return_30d', 'N/A')}%\n"
            f"  Bullish tickers from analogues: {market_reactions.get('most_common_bullish', [])}\n"
            f"  Bearish tickers from analogues: {market_reactions.get('most_common_bearish', [])}\n\n"
            f"Context:\n{context}"
        )

        llm_output, fallback_used, model_used = await self._call_llm(
            system_prompt=HISTORICAL_RAG_SYSTEM,
            user_prompt=user_prompt,
            output_schema="JSON object with best_analogues, pattern_recognition, typical_market_reaction, anomaly_detection, analogical_confidence",
        )

        parsed = self._extract_json_from_output(llm_output)
        if parsed is None:
            parsed = self._deterministic_fallback(top_analogues, market_reactions)

        parsed["_raw_analogues"] = top_analogues[:5]
        parsed["_market_reactions"] = market_reactions
        state["historical_analysis"] = parsed

        elapsed = (time.perf_counter() - start) * 1000
        ctx = self._build_agent_context(state, parsed, execution_time_ms=elapsed, fallback_used=fallback_used, model_used=model_used)
        state.setdefault("agent_contexts", {})[self.agent_id] = ctx
        self._log_step(state, "COMPLETE", f"{len(top_analogues)} analogues, {elapsed:.0f}ms")
        return state

    def _format_analogues(self, analogues: List[Dict[str, Any]]) -> str:
        lines = []
        for i, a in enumerate(analogues[:8], 1):
            title = a.get("event_title", "Unknown")
            etype = a.get("event_type", "")
            date_str = a.get("event_date", "")
            sim = a.get("similarity", 0)
            sectors = a.get("sectors", "")
            bullish = a.get("bullish_tickers", "")
            bearish = a.get("bearish_tickers", "")
            conf = a.get("confidence", {})
            conf_level = conf.get("level", "unknown") if isinstance(conf, dict) else "unknown"

            lines.append(
                f"{i}. {title} (sim={sim:.3f}, conf={conf_level})\n"
                f"   Type: {etype} | Date: {date_str}\n"
                f"   Sectors: {sectors}\n"
                f"   Bullish: {bullish} | Bearish: {bearish}"
            )
        return "\n".join(lines)

    def _deterministic_fallback(
        self, analogues: List[Dict[str, Any]], market_reactions: Dict[str, Any],
    ) -> Dict[str, Any]:
        best = analogues[0] if analogues else {}
        return {
            "best_analogues": [
                {
                    "event_title": best.get("event_title", "N/A"),
                    "event_date": best.get("event_date", ""),
                    "similarity_score": best.get("similarity", 0),
                    "key_similarities": ["Deterministic match"],
                    "key_differences": ["LLM unavailable for deep analysis"],
                    "market_outcome_5d": f"{market_reactions.get('avg_market_return_5d', 'N/A')}%",
                    "market_outcome_30d": f"{market_reactions.get('avg_market_return_30d', 'N/A')}%",
                    "sectors_affected": best.get("sectors", "").split(",") if best.get("sectors") else [],
                }
            ],
            "pattern_recognition": "LLM unavailable",
            "typical_market_reaction": {
                "equity_impact": "See market reaction data",
                "sector_rotation": "Unknown",
                "safe_haven_flows": "Unknown",
                "volatility_impact": f"{market_reactions.get('avg_volatility_change_pct', 'N/A')}% avg change",
            },
            "anomaly_detection": "Unable to assess (deterministic fallback)",
            "analogical_confidence": 0.3,
        }
