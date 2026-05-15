from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.models.geopol_event import GeoPolEvent
from app.services.agent.base import BaseAgent
from app.services.gdelt.client import GDELTClient


class GeopoliticalAnalystAgent(BaseAgent):
    """Analyzes geopolitical events and assesses sector/stock impact."""

    def __init__(self, gdelt_client: Optional[GDELTClient] = None) -> None:
        super().__init__(
            agent_id="geopol-agent",
            name="Geopolitical Analyst",
        )
        self.gdelt = gdelt_client or GDELTClient()

    async def run(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        query = input_data.get("query", "")
        event_ids = input_data.get("event_ids", [])
        events = input_data.get("events", [])

        if not events and not event_ids and not query:
            return {"status": "error", "message": "No query, event_ids, or events provided."}

        if not events and query:
            raw_events = await self.gdelt.fetch_events(
                query=query,
                max_records=input_data.get("max_records", 50),
            )
            from app.services.gdelt.parser import GDELTParser
            events = [GDELTParser.parse_event(e) for e in raw_events if GDELTParser.parse_event(e)]

        analysis_prompt = (
            f"You are a senior geopolitical risk analyst. Conduct a DEEP-DIVE analysis of the following events "
            f"and their potential cascading impacts on global financial markets.\n\n"
            f"Events:\n{self._format_events(events)}\n\n"
            f"Please provide a comprehensive report covering:\n"
            f"1. GEOPOLITICAL RISK ASSESSMENT: Analyze the core drivers, structural shifts, and potential for escalation.\n"
            f"2. MACROECONOMIC IMPACT: Assess inflationary pressures, interest rate implications, and currency volatility.\n"
            f"3. SECTOR-LEVEL GRANULARITY: Identify 10-15 affected sectors (e.g., semiconductors, defense, rare earths, logistics) and rank them by impact severity (Bullish/Bearish).\n"
            f"4. STOCK-SPECIFIC TARGETS: List 20-30 specific stocks (with tickers) that will likely see high volatility or directional shifts.\n"
            f"5. CROSS-ASSET CORRELATIONS: How does this affect commodities (Oil, Gold, Copper) vs. Treasury yields?\n"
            f"6. RISK OUTCOMES: Describe 3 potential scenarios (Baseline, Extreme Escalation, De-escalation).\n"
            f"7. STRATEGIC RECOMMENDATIONS: Specific hedging strategies and alpha-generating opportunities for institutional investors.\n"
            f"8. CONFIDENCE LEVEL: Provide an overall confidence score (0-100%) and identify data gaps."
        )


        llm_output = await self._call_llm(
            system_prompt="You are a senior geopolitical risk analyst for a hedge fund.",
            user_prompt=analysis_prompt,
        )

        self._add_to_memory("user", str(input_data))
        self._add_to_memory("assistant", llm_output)

        return {
            "agent": self.agent_id,
            "status": "completed",
            "events_analyzed": len(events),
            "analysis": llm_output,
            "affected_sectors": self._extract_sectors(events),
            "severity_score": self._compute_avg_severity(events),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _format_events(self, events: List[GeoPolEvent]) -> str:
        parts = []
        for i, e in enumerate(events[:10], 1):
            parts.append(
                f"{i}. [{e.event_type}] {e.title} ({e.location}, severity={e.severity})\n"
                f"   {e.description[:200]}...\n"
                f"   Sectors: {', '.join(e.affected_sectors)}"
            )
        return "\n".join(parts)

    def _extract_sectors(self, events: List[GeoPolEvent]) -> List[str]:
        sectors = set()
        for e in events:
            sectors.update(e.affected_sectors)
        return list(sectors)

    def _compute_avg_severity(self, events: List[GeoPolEvent]) -> float:
        if not events:
            return 0.0
        return sum(e.severity for e in events) / len(events)
