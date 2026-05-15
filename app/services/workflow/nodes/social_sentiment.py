from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from app.services.workflow.base import EnhancedAgentNode
from app.services.workflow.prompts import SOCIAL_SENTIMENT_SYSTEM
from app.services.workflow.state import WorkflowState
from app.services.workflow.tools import AgentTools


class SocialSentimentNode(EnhancedAgentNode):
    """Agent node: analyzes social media sentiment for financial signals."""

    def __init__(self, tools: Optional[AgentTools] = None) -> None:
        super().__init__(
            agent_id="social-sentiment",
            agent_name="Social Sentiment Agent",
        )
        self._tools_inst = tools or AgentTools()

    def _goals(self) -> str:
        return (
            "Analyze social media sentiment from Reddit and other sources. "
            "Extract retail sentiment signals, detect emerging narratives, "
            "identify notable ticker mentions, and assess fear/greed dynamics."
        )

    async def __call__(self, state: WorkflowState) -> WorkflowState:
        start = time.perf_counter()
        self._log_step(state, "START")

        query = state.get("query", "")
        tickers = state.get("tickers", [])
        news_analysis = state.get("news_analysis", {}) or {}

        search_terms = [query]
        if tickers:
            search_terms.extend(tickers[:5])

        all_signals: List[Dict[str, Any]] = []
        all_posts: List[Dict[str, Any]] = []

        for term in search_terms[:3]:
            sentiment = await self._tools_inst.fetch_reddit_sentiment(
                query=term, limit=30,
            )
            all_signals.append(sentiment)

        aggregated = self._aggregate_sentiments(all_signals)

        context = self._build_context(state)
        news_sectors = [
            s.get("sector", "") for s in (news_analysis.get("primary_sectors_impacted") or [])
        ]
        sector_str = ", ".join(news_sectors) if news_sectors else "general"

        user_prompt = (
            f"Analyze social sentiment data for this geopolitical event.\n\n"
            f"Query: {query}\n"
            f"Tickers of interest: {', '.join(tickers)}\n"
            f"News context sectors: {sector_str}\n\n"
            f"Aggregated sentiment data:\n"
            f"Overall Score: {aggregated.get('overall_score', 0):.3f}\n"
            f"Confidence: {aggregated.get('confidence', 0):.3f}\n"
            f"Signal: {aggregated.get('signal', 'neutral')}\n"
            f"Volume: {aggregated.get('volume', 0)}\n"
            f"Distribution: {aggregated.get('distribution', {})}\n"
            f"Top Keywords: {', '.join(aggregated.get('top_keywords', []))}\n\n"
            f"Context:\n{context}"
        )

        llm_output, fallback_used, model_used = await self._call_llm(
            system_prompt=SOCIAL_SENTIMENT_SYSTEM,
            user_prompt=user_prompt,
            output_schema="JSON object with overall_sentiment, sentiment_score, sentiment_confidence, retail_vs_institutional_divergence, key_narratives, signal_strength, notable_tickers_mentioned, fear_and_greed_assessment, analysis",
        )

        parsed = self._extract_json_from_output(llm_output)
        if parsed is None:
            parsed = self._deterministic_fallback(aggregated)

        parsed["_aggregated_sentiment"] = aggregated
        state["sentiment_posts"] = all_posts
        state["sentiment_analysis"] = parsed

        elapsed = (time.perf_counter() - start) * 1000
        ctx = self._build_agent_context(state, parsed, execution_time_ms=elapsed, fallback_used=fallback_used, model_used=model_used)
        state.setdefault("agent_contexts", {})[self.agent_id] = ctx
        self._log_step(state, "COMPLETE", f"score={aggregated.get('overall_score', 0):.3f}, {elapsed:.0f}ms")
        return state

    def _aggregate_sentiments(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not signals:
            return {"overall_score": 0.0, "confidence": 0.0, "signal": "neutral",
                    "volume": 0, "distribution": {}, "top_keywords": []}

        total_score = sum(s.get("overall_score", 0) for s in signals)
        total_conf = sum(s.get("confidence", 0) for s in signals)
        total_volume = sum(s.get("volume", 0) for s in signals)
        count = len(signals)

        keywords = []
        for s in signals:
            keywords.extend(s.get("top_keywords", []))

        dist: Dict[str, int] = {}
        for s in signals:
            for k, v in s.get("distribution", {}).items():
                dist[k] = dist.get(k, 0) + v

        avg_score = total_score / count if count else 0
        avg_conf = total_conf / count if count else 0

        if avg_score > 0.15 and avg_conf > 0.3:
            signal = "bullish"
        elif avg_score < -0.15 and avg_conf > 0.3:
            signal = "bearish"
        else:
            signal = "neutral"

        return {
            "overall_score": round(avg_score, 4),
            "confidence": round(avg_conf, 4),
            "signal": signal,
            "volume": total_volume,
            "distribution": dist,
            "top_keywords": list(dict.fromkeys(keywords))[:15],
        }

    def _deterministic_fallback(self, aggregated: Dict[str, Any]) -> Dict[str, Any]:
        signal = aggregated.get("signal", "neutral")
        return {
            "overall_sentiment": signal,
            "sentiment_score": aggregated.get("overall_score", 0),
            "sentiment_confidence": aggregated.get("confidence", 0),
            "retail_vs_institutional_divergence": "unknown (LLM unavailable)",
            "key_narratives": [f"Social sentiment signal: {signal}"],
            "signal_strength": "weak" if aggregated.get("volume", 0) < 20 else "moderate",
            "notable_tickers_mentioned": [],
            "fear_and_greed_assessment": "neutral (deterministic fallback)",
            "analysis": f"Deterministic analysis: sentiment={signal}, score={aggregated.get('overall_score', 0):.2f}",
        }
