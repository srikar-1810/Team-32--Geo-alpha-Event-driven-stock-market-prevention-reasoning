from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.services.workflow.base import EnhancedAgentNode
from app.services.workflow.prompts import NEWS_INTELLIGENCE_SYSTEM
from app.services.workflow.state import WorkflowState
from app.services.workflow.tools import AgentTools


class NewsIntelligenceNode(EnhancedAgentNode):
    """Agent node: analyzes live geopolitical events via GDELT."""

    def __init__(self, tools: Optional[AgentTools] = None) -> None:
        super().__init__(
            agent_id="news-intelligence",
            agent_name="News Intelligence Agent",
        )
        self._tools_inst = tools or AgentTools()

    def _goals(self) -> str:
        return (
            "Fetch and analyze live geopolitical events from GDELT. "
            "Classify event types, assess geopolitical significance, "
            "identify affected regions and sectors, and generate "
            "a market narrative with uncertainty factors."
        )

    async def __call__(self, state: WorkflowState) -> WorkflowState:
        start = time.perf_counter()
        self._log_step(state, "START", f"query={state.get('query', '')[:60]}")

        query = state.get("query", "")
        tickers = state.get("tickers", [])
        location = state.get("location", "")

        search_terms = [query]
        if location and location not in query:
            search_terms.append(f"{query} {location}")
        if tickers:
            search_terms.append(f"{' '.join(tickers[:3])} {query}")

        all_events: List[Dict[str, Any]] = []
        for term in search_terms[:2]:
            events = await self._tools_inst.fetch_gdelt_events(term, max_records=15, days_back=3)
            all_events.extend(events)

        cameo_events = await self._tools_inst.fetch_gdelt_events_cameo(
            query, max_records=15, days_back=3,
        )
        for ce in cameo_events:
            if isinstance(ce, dict):
                all_events.append(ce)

        seen_urls: set = set()
        unique_events: list = []
        for e in all_events:
            url = e.get("source_url", e.get("url", ""))
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_events.append(e)

        state["news_events"] = unique_events[:20]

        context = self._build_context(state)
        events_summary = self._summarize_events(unique_events[:10])

        user_prompt = (
            f"Analyze these recent geopolitical events and their market implications.\n\n"
            f"Query: {query}\n"
            f"Location: {location}\n"
            f"Tickers: {', '.join(tickers)}\n\n"
            f"Recent events ({len(unique_events)} total):\n{events_summary}\n\n"
            f"Context:\n{context}"
        )

        llm_output, fallback_used, model_used = await self._call_llm(
            system_prompt=NEWS_INTELLIGENCE_SYSTEM,
            user_prompt=user_prompt,
            output_schema="JSON object with risk_level, event_type_classification, geopolitical_significance, affected_regions, primary_sectors_impacted, key_findings, market_narrative, uncertainty_factors, data_quality_assessment",
        )

        parsed = self._parse_json_output(llm_output)
        if parsed is None:
            parsed = self._deterministic_fallback(state, unique_events)

        state["news_analysis"] = parsed
        elapsed = (time.perf_counter() - start) * 1000
        ctx = self._build_agent_context(state, parsed, execution_time_ms=elapsed, fallback_used=fallback_used, model_used=model_used)
        state.setdefault("agent_contexts", {})[self.agent_id] = ctx
        self._log_step(state, "COMPLETE", f"{len(unique_events)} events, {elapsed:.0f}ms")
        return state

    def _summarize_events(self, events: List[Dict[str, Any]]) -> str:
        lines = []
        for i, e in enumerate(events[:10], 1):
            title = e.get("title", e.get("event_title", "Unknown"))
            etype = e.get("event_type", e.get("type", "Unknown"))
            loc = e.get("location", e.get("Location", "Unknown"))
            severity = e.get("severity", e.get("goldstein_scale", 0))
            desc = str(e.get("description", e.get("description", "")))[:150]
            lines.append(f"{i}. [{etype}] {title} ({loc}, severity={severity})\n   {desc}")
        return "\n".join(lines)

    def _deterministic_fallback(
        self, state: WorkflowState, events: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        self._log_step(state, "FALLBACK", "Using deterministic analysis")
        event_types: Dict[str, int] = {}
        locations: set = set()
        total_severity = 0.0

        for e in events:
            et = e.get("event_type", "unknown")
            event_types[et] = event_types.get(et, 0) + 1
            loc = e.get("location", "")
            if loc:
                locations.add(loc)
            total_severity += e.get("severity", e.get("goldstein_scale", 0))

        primary_type = max(event_types, key=event_types.get) if event_types else "unknown"
        avg_severity = total_severity / len(events) if events else 0

        high_severity_keywords = ["war", "attack", "sanctions", "crisis", "nuclear", "terrorism"]
        risk_level = "high" if any(k in primary_type.lower() for k in high_severity_keywords) else \
                     "moderate" if avg_severity > 3 else "low"

        return {
            "risk_level": risk_level,
            "event_type_classification": primary_type,
            "geopolitical_significance": f"{len(events)} events detected of type {primary_type}",
            "affected_regions": list(locations),
            "primary_sectors_impacted": [],
            "key_findings": [f"Detected {len(events)} geopolitical events", f"Primary type: {primary_type}"],
            "market_narrative": f"Multiple {primary_type} events detected",
            "uncertainty_factors": ["LLM unavailable, deterministic analysis used"],
            "data_quality_assessment": "low",
        }
