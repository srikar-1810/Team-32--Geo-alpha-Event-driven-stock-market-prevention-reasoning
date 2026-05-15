from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from app.services.workflow.base import EnhancedAgentNode
from app.services.workflow.prompts import REPORT_GENERATION_SYSTEM
from app.services.workflow.state import WorkflowState
from app.services.workflow.tools import AgentTools


class ReportGenerationNode(EnhancedAgentNode):
    """Agent node: generates the final market intelligence report."""

    def __init__(self, tools: Optional[AgentTools] = None) -> None:
        super().__init__(
            agent_id="report-generation",
            agent_name="Report Generation Agent",
        )
        self._tools_inst = tools or AgentTools()

    def _goals(self) -> str:
        return (
            "Synthesize all upstream agent analyses into a polished, "
            "actionable market intelligence report. Structure the report "
            "with executive summary, key judgments, sector impacts, "
            "stock recommendations, risk summary, and confidence scores."
        )

    async def __call__(self, state: WorkflowState) -> WorkflowState:
        start = time.perf_counter()
        self._log_step(state, "START")

        query = state.get("query", "")
        tickers = state.get("tickers", [])

        news = state.get("news_analysis", {}) or {}
        sentiment = state.get("sentiment_analysis", {}) or {}
        historical = state.get("historical_analysis", {}) or {}
        market = state.get("market_analysis", {}) or {}
        risk = state.get("risk_assessment", {}) or {}
        confidence = state.get("confidence_analysis", {}) or {}
        agent_contexts = state.get("agent_contexts", {})

        summary_parts: List[str] = []
        summary_parts.append(f"News Risk: {news.get('risk_level', 'N/A')}")
        summary_parts.append(
            f"Sentiment: {sentiment.get('overall_sentiment', 'neutral')} "
            f"(score={sentiment.get('sentiment_score', 0):.2f})"
        )
        summary_parts.append(f"Historical Analogues: {historical.get('analogical_confidence', 0):.2f}")
        summary_parts.append(f"Risk Score: {risk.get('overall_risk_score', 0):.2f} ({risk.get('risk_level', 'N/A')})")
        summary_parts.append(f"Confidence: {confidence.get('overall_confidence', 0):.2f} ({confidence.get('confidence_level', 'N/A')})")

        sector_matrix = market.get("sector_impact_matrix", [])
        sector_text = "\n".join(
            f"  {s.get('sector', '?')} ({s.get('etf_ticker', '')}): "
            f"{s.get('impact_direction', 'neutral')} | conf={s.get('confidence', 0):.2f} | "
            f"horizon={s.get('time_horizon', 'medium')}"
            for s in sector_matrix
        ) if sector_matrix else "  No sector analysis available"

        stock_picks = market.get("stock_impact_picks", [])
        stock_text = "\n".join(
            f"  {s.get('ticker', '?')}: {s.get('direction', 'watch')} | "
            f"conviction={s.get('conviction', 'low')} | {s.get('reasoning', '')[:150]}"
            for s in stock_picks
        ) if stock_picks else "  No stock picks available"

        analogues_raw = historical.get("_raw_analogues", [])
        historical_text = "\n".join(
            f"  {a.get('event_title', '?')} (sim={a.get('similarity', 0):.3f})"
            for a in analogues_raw[:3]
        ) if analogues_raw else "  No historical analogues found"

        risk_factors = risk.get("risk_breakdown", [])
        risk_text = "\n".join(
            f"  {r.get('risk_factor', '?')}: sev={r.get('severity', 0):.2f} "
            f"prob={r.get('probability', 0):.2f}"
            for r in risk_factors
        ) if risk_factors else "  No risk breakdown available"

        tail_risks = risk.get("tail_risk_scenarios", [])
        tail_text = "\n".join(
            f"  {t.get('scenario', '?')} (prob={t.get('probability', 0):.2f})"
            for t in tail_risks
        ) if tail_risks else "  No tail risks identified"

        agent_errors = [
            f"{aid}: {ctx.get('error', 'unknown')}"
            for aid, ctx in agent_contexts.items()
            if isinstance(ctx, dict) and ctx.get("status") == "failed"
        ]

        user_prompt = (
            f"Generate a final market intelligence report synthesizing all agent analyses.\n\n"
            f"Event: {query}\n"
            f"Tickers: {', '.join(tickers)}\n\n"
            f"=== EXECUTIVE SUMMARY ===\n"
            f"{' | '.join(summary_parts)}\n\n"
            f"=== GEOPOLITICAL ANALYSIS ===\n"
            f"Risk Level: {news.get('risk_level', 'N/A')}\n"
            f"Classification: {news.get('event_type_classification', 'N/A')}\n"
            f"Narrative: {news.get('market_narrative', '')}\n"
            f"Key Findings: {news.get('key_findings', [])}\n"
            f"Affected Regions: {news.get('affected_regions', [])}\n\n"
            f"=== SOCIAL SENTIMENT ===\n"
            f"Overall: {sentiment.get('overall_sentiment', 'neutral')}\n"
            f"Key Narratives: {sentiment.get('key_narratives', [])}\n"
            f"Signal Strength: {sentiment.get('signal_strength', 'weak')}\n"
            f"Analysis: {sentiment.get('analysis', '')}\n\n"
            f"=== HISTORICAL ANALOGUES ===\n"
            f"Analogical Confidence: {historical.get('analogical_confidence', 0):.3f}\n"
            f"Pattern Recognition: {historical.get('pattern_recognition', '')}\n"
            f"Analogues:\n{historical_text}\n\n"
            f"=== SECTOR IMPACTS ===\n{sector_text}\n\n"
            f"=== STOCK RECOMMENDATIONS ===\n{stock_text}\n\n"
            f"=== RISK ASSESSMENT ===\n"
            f"Overall Score: {risk.get('overall_risk_score', 0):.2f}\n"
            f"Level: {risk.get('risk_level', 'N/A')}\n"
            f"Confidence: {confidence.get('overall_confidence', 0):.2f} ({confidence.get('confidence_level', 'N/A')})\n"
            f"Risk Breakdown:\n{risk_text}\n"
            f"Tail Risk Scenarios:\n{tail_text}\n"
            f"Volatility Outlook: {risk.get('volatility_outlook', {}).get('expected_regime', 'unknown')}\n\n"
            f"=== AGENT EXECUTION ===\n"
            f"Agents Completed: {sum(1 for c in agent_contexts.values() if isinstance(c, dict) and c.get('status') == 'completed')}\n"
            f"Agent Errors: {agent_errors if agent_errors else 'None'}\n\n"
            f"Format a professional report with sections: "
            f"Title, Executive Summary, Key Judgments, Geopolitical Analysis, "
            f"Social Sentiment, Historical Context, Sector Impact Table, "
            f"Top Stock Recommendations, Risk Summary, Data Quality Notes."
        )

        llm_output, fallback_used, model_used = await self._call_llm(
            system_prompt=REPORT_GENERATION_SYSTEM,
            user_prompt=user_prompt,
            output_schema="JSON object with title, report_type, executive_summary, key_judgments, geopolitical_analysis_summary, social_sentiment_summary, historical_context, sector_impact_table, top_stock_recommendations, risk_summary, confidence_score, data_quality_notes, disclaimers",
        )

        parsed = self._extract_json_from_output(llm_output)
        if parsed is None:
            parsed = self._deterministic_fallback(query, tickers, summary_parts)

        parsed["_all_agent_outputs"] = {
            "news_intelligence": news,
            "social_sentiment": sentiment,
            "historical_analyst": historical,
            "market_strategist": market,
            "risk_analysis": risk,
        }

        state["report"] = parsed

        elapsed = (time.perf_counter() - start) * 1000
        ctx = self._build_agent_context(state, parsed, execution_time_ms=elapsed, fallback_used=fallback_used, model_used=model_used)
        state.setdefault("agent_contexts", {})[self.agent_id] = ctx
        self._log_step(state, "COMPLETE", f"report generated, {elapsed:.0f}ms")
        return state

    def _deterministic_fallback(
        self, query: str, tickers: List[str], summary_parts: List[str],
    ) -> Dict[str, Any]:
        return {
            "title": f"Market Intelligence Report: {query[:80]}",
            "report_type": "standard",
            "executive_summary": " | ".join(summary_parts),
            "key_judgments": [
                {"judgment": "Event detected and analyzed", "confidence": "medium",
                 "evidence": "Multi-agent pipeline completed"}
            ],
            "geopolitical_analysis_summary": "See news intelligence output",
            "social_sentiment_summary": "See sentiment analysis output",
            "historical_context": "See historical analogue output",
            "sector_impact_table": [],
            "top_stock_recommendations": [
                {"ticker": t, "action": "watch", "conviction": "low",
                 "rationale": "LLM unavailable for final synthesis", "risk_factors": []}
                for t in tickers
            ],
            "risk_summary": "LLM unavailable for detailed risk assessment",
            "confidence_score": 0.3,
            "data_quality_notes": ["Report generated with deterministic fallback"],
            "disclaimers": ["This report was generated with limited LLM availability."],
        }
