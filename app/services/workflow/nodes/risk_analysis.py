from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from app.services.workflow.base import EnhancedAgentNode
from app.services.workflow.prompts import RISK_ANALYSIS_SYSTEM
from app.services.workflow.state import WorkflowState
from app.services.workflow.tools import AgentTools


class RiskAnalysisNode(EnhancedAgentNode):
    """Agent node: quantifies risk, computes confidence, identifies tail scenarios."""

    def __init__(self, tools: Optional[AgentTools] = None) -> None:
        super().__init__(
            agent_id="risk-analysis",
            agent_name="Risk Analysis Agent",
        )
        self._tools_inst = tools or AgentTools()

    def _goals(self) -> str:
        return (
            "Quantify overall risk from the geopolitical event. "
            "Compute confidence levels based on data quality, multi-agent agreement, "
            "and historical precedent. Identify tail risk scenarios "
            "and provide volatility outlook."
        )

    async def __call__(self, state: WorkflowState) -> WorkflowState:
        start = time.perf_counter()
        self._log_step(state, "START")

        news = state.get("news_analysis", {}) or {}
        sentiment = state.get("sentiment_analysis", {}) or {}
        historical = state.get("historical_analysis", {}) or {}
        market = state.get("market_analysis", {}) or {}
        agent_contexts = state.get("agent_contexts", {})

        news_risk = news.get("risk_level", "moderate")
        sentiment_score = sentiment.get("sentiment_score", 0)
        sentiment_conf = sentiment.get("sentiment_confidence", 0)
        analogical_conf = historical.get("analogical_confidence", 0.3)

        confidence_signals = self._compute_confidence_signals(
            news_risk=news_risk,
            sentiment_score=sentiment_score,
            sentiment_conf=sentiment_conf,
            analogical_conf=analogical_conf,
            agent_contexts=agent_contexts,
            market=market,
        )

        user_prompt = (
            f"Perform comprehensive risk analysis for this geopolitical event.\n\n"
            f"Event: {state.get('query', '')}\n"
            f"Tickers: {', '.join(state.get('tickers', []))}\n\n"
            f"News Risk Level: {news_risk}\n"
            f"Sentiment Score: {sentiment_score:.3f} (conf={sentiment_conf:.3f})\n"
            f"Analogical Confidence: {analogical_conf:.3f}\n\n"
            f"Confidence Signals:\n"
            f"  Data Quality: {confidence_signals.get('data_quality', 'medium')}\n"
            f"  Agent Agreement: {confidence_signals.get('agent_agreement', 'unknown')}\n"
            f"  Historical Support: {confidence_signals.get('historical_support', 'unknown')}\n"
            f"  Confidence Score: {confidence_signals.get('overall_confidence', 0.5):.3f}\n\n"
            f"Sector impacts from market strategist:\n"
            f"  {[s.get('sector', '') for s in market.get('sector_impact_matrix', [])]}\n\n"
            f"Stock picks:\n"
            f"  {[s.get('ticker', '') for s in market.get('stock_impact_picks', [])]}\n\n"
            f"Tail risks from market analysis:\n"
            f"  {market.get('macro_tail_risks', [])}"
        )

        llm_output, fallback_used, model_used = await self._call_llm(
            system_prompt=RISK_ANALYSIS_SYSTEM,
            user_prompt=user_prompt,
            output_schema="JSON object with overall_risk_score, risk_level, risk_breakdown, confidence_assessment, tail_risk_scenarios, volatility_outlook",
        )

        parsed = self._extract_json_from_output(llm_output)
        if parsed is None:
            parsed = self._deterministic_fallback(
                news_risk, confidence_signals, market,
            )

        parsed["_confidence_signals"] = confidence_signals

        risk_score = parsed.get("overall_risk_score", 0.5)
        risk_level = parsed.get("risk_level", news_risk)
        if risk_score < 0.3:
            risk_level = "low"
        elif risk_score < 0.6:
            risk_level = "moderate"
        elif risk_score < 0.8:
            risk_level = "high"
        else:
            risk_level = "severe"

        parsed["overall_risk_score"] = round(risk_score, 4)
        parsed["risk_level"] = risk_level

        state["risk_assessment"] = parsed
        state["confidence_analysis"] = parsed.get("confidence_assessment", {})

        elapsed = (time.perf_counter() - start) * 1000
        ctx = self._build_agent_context(state, parsed, execution_time_ms=elapsed, fallback_used=fallback_used, model_used=model_used)
        state.setdefault("agent_contexts", {})[self.agent_id] = ctx
        self._log_step(state, "COMPLETE", f"risk={risk_level}, conf={parsed.get('confidence_assessment', {}).get('overall_confidence', 0):.2f}, {elapsed:.0f}ms")
        return state

    def _compute_confidence_signals(
        self,
        news_risk: str,
        sentiment_score: float,
        sentiment_conf: float,
        analogical_conf: float,
        agent_contexts: Dict[str, Any],
        market: Dict[str, Any],
    ) -> Dict[str, Any]:
        risk_scores = {"low": 0.2, "moderate": 0.5, "high": 0.8, "severe": 0.95}
        news_conf = 1.0 - risk_scores.get(news_risk, 0.5)

        completed_agents = sum(
            1 for ctx in agent_contexts.values()
            if isinstance(ctx, dict) and ctx.get("status") == "completed"
        )
        total_agents = max(len(agent_contexts), 1)
        agent_agreement_ratio = completed_agents / total_agents

        market_conf = 0.5
        sector_matrix = market.get("sector_impact_matrix", [])
        if sector_matrix:
            avg_conf = sum(
                s.get("confidence", 0) for s in sector_matrix
            ) / len(sector_matrix)
            market_conf = avg_conf

        weights = {
            "news_data_quality": 0.25,
            "sentiment_confidence": 0.20,
            "historical_analogical": 0.20,
            "agent_agreement": 0.15,
            "market_data_quality": 0.20,
        }
        score = (
            weights["news_data_quality"] * news_conf +
            weights["sentiment_confidence"] * sentiment_conf +
            weights["historical_analogical"] * analogical_conf +
            weights["agent_agreement"] * agent_agreement_ratio +
            weights["market_data_quality"] * market_conf
        )

        if score >= 0.7:
            level = "high"
        elif score >= 0.4:
            level = "medium"
        else:
            level = "low"

        return {
            "overall_confidence": round(score, 4),
            "confidence_level": level,
            "data_quality": "high" if news_conf > 0.7 else "medium" if news_conf > 0.4 else "low",
            "agent_agreement": f"{completed_agents}/{total_agents} agents completed",
            "historical_support": "strong" if analogical_conf > 0.7 else "moderate" if analogical_conf > 0.4 else "weak",
        }

    def _deterministic_fallback(
        self, news_risk: str, confidence: Dict[str, Any], market: Dict[str, Any],
    ) -> Dict[str, Any]:
        risk_scores = {"low": 0.2, "moderate": 0.5, "high": 0.8, "severe": 0.95}
        score = risk_scores.get(news_risk, 0.5)
        return {
            "overall_risk_score": score,
            "risk_level": news_risk,
            "risk_breakdown": [
                {"risk_factor": "Geopolitical event", "severity": score,
                 "probability": 0.6, "impact_description": news_risk,
                 "mitigation": "Monitor developments"}
            ],
            "confidence_assessment": {
                "overall_confidence": confidence.get("overall_confidence", 0.5),
                "confidence_level": confidence.get("confidence_level", "medium"),
                "confidence_signals": [],
                "data_gaps": ["LLM unavailable for deep analysis"],
            },
            "tail_risk_scenarios": [
                {"scenario": "Escalation", "probability": 0.3,
                 "market_impact": "High volatility", "signs_to_monitor": ["News flow"]}
            ],
            "volatility_outlook": {
                "expected_regime": "moderate",
                "vix_implication": "Likely elevated",
                "sector_volatility_divergences": [],
            },
        }
