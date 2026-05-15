from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from app.logging_config import get_logger
from app.services.simulation.models import ParsedScenario

logger = get_logger(__name__)

SCENARIO_PARSER_SYSTEM = """You are an expert geopolitical scenario analyst and macroeconomic strategist. Parse the user's hypothetical event into a deeply structured scenario.
Consider the full geopolitical context, historical precedents, and cascading economic implications.

Output ONLY valid JSON with these fields:
{
  "event_type": "string (one of: war, sanctions, election, natural_disaster, pandemic, trade_dispute, coup, cyberattack, treaty, assassination, protest, debt_crisis, energy_crisis, currency_crisis, regulatory_change, technology_disruption, terrorism, climate_event, supply_shock, monetary_policy, corporate_collapse, infrastructure_failure, migration_crisis, space_event, ai_disruption, social_media_event, gaming_industry, entertainment_industry, sports_disruption, food_crisis, water_crisis, nuclear_incident, diplomatic_incident, market_crash, housing_crisis, labor_strike, piracy, blockade)",
  "title": "string (concise 5-10 word professional title)",
  "description": "string (2-3 paragraph detailed description covering what, why, how, and cascading effects)",
  "location": "string (primary geographic location)",
  "countries": ["list of ALL affected countries, both directly and indirectly"],
  "actors": ["list of all key actors: governments, companies, organizations, individuals"],
  "severity_estimate": "float 0.0-10.0 (estimated geopolitical severity based on historical precedent)",
  "estimated_timeline": "string (immediate/short_term/medium_term/long_term + reasoning)",
  "economic_scope": "string (local/regional/global)",
  "uncertainty_factors": ["list of 5-8 key uncertainty factors that could change the outcome"]
}"""


class ScenarioParser:
    """Parses free-text what-if queries into structured scenarios."""

    def __init__(self) -> None:
        self._model: Optional[str] = None

    async def parse(self, query: str) -> ParsedScenario:
        logger.info("Parsing scenario: %s", query[:80])
        llm_output = await self._call_llm(query)
        parsed = self._parse_llm_output(llm_output, query)
        return parsed

    async def _call_llm(self, query: str) -> str:
        from app.utils.llm_client import create_llm_client
        from app.config import settings

        client = create_llm_client()
        try:
            response = await client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": SCENARIO_PARSER_SYSTEM},
                    {"role": "user", "content": f"What if: {query}"},
                ],
                temperature=0.1,
                max_tokens=2048,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.warning("LLM scenario parse failed: %s", e)
            return self._deterministic_fallback(query)

    def _parse_llm_output(self, text: str, original_query: str) -> ParsedScenario:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                except json.JSONDecodeError:
                    data = {}
            else:
                data = {}

        if not data or "event_type" not in data:
            return self._deterministic_parse(original_query)

        return ParsedScenario(
            event_type=data.get("event_type", "unknown"),
            title=data.get("title", original_query[:80]),
            description=data.get("description", original_query),
            location=data.get("location", "Global"),
            countries=data.get("countries", []),
            actors=data.get("actors", []),
            severity_estimate=float(data.get("severity_estimate", 5.0)),
            estimated_timeline=data.get("estimated_timeline", "medium_term"),
            economic_scope=data.get("economic_scope", "regional"),
            uncertainty_factors=data.get("uncertainty_factors", ["LLM unavailable"]),
            original_query=original_query,
        )

    def _deterministic_fallback(self, query: str) -> str:
        return json.dumps(self._deterministic_parse(query).to_dict())

    def _deterministic_parse(self, query: str) -> ParsedScenario:
        q = query.lower()

        if any(w in q for w in ["war", "invasion", "military", "conflict", "attack"]):
            etype, sev, scope = "war", 8.0, "regional"
        elif any(w in q for w in ["sanction", "embargo", "tariff", "trade"]):
            etype, sev, scope = "sanctions", 6.0, "global"
        elif any(w in q for w in ["election", "vote", "president"]):
            etype, sev, scope = "election", 5.0, "regional"
        elif any(w in q for w in ["crisis", "collapse", "default", "recession", "debt"]):
            etype, sev, scope = "financial_crisis", 7.0, "global"
        elif any(w in q for w in ["disaster", "earthquake", "hurricane", "flood", "tsunami", "volcano"]):
            etype, sev, scope = "natural_disaster", 7.0, "regional"
        elif any(w in q for w in ["pandemic", "virus", "outbreak", "epidemic", "disease"]):
            etype, sev, scope = "pandemic", 8.0, "global"
        elif any(w in q for w in ["cyber", "hack", "ransomware", "data breach"]):
            etype, sev, scope = "cyberattack", 6.0, "global"
        elif any(w in q for w in ["treaty", "agreement", "deal", "negotiation", "summit", "alliance"]):
            etype, sev, scope = "diplomacy", 4.0, "global"
        elif any(w in q for w in ["protest", "riot", "coup", "revolt", "revolution", "uprising"]):
            etype, sev, scope = "civil_unrest", 6.0, "regional"
        elif any(w in q for w in ["energy", "oil", "gas", "pipeline", "opec", "petrol", "fuel"]):
            etype, sev, scope = "energy_crisis", 7.0, "global"
        elif any(w in q for w in ["currency", "dollar", "euro", "yuan", "devalue", "forex", "exchange rate"]):
            etype, sev, scope = "currency_crisis", 6.0, "global"
        elif any(w in q for w in ["regulation", "ban", "law", "policy", "antitrust", "fda", "sec"]):
            etype, sev, scope = "regulatory_change", 5.0, "regional"
        elif any(w in q for w in ["ai", "artificial intelligence", "chatgpt", "robot", "automation"]):
            etype, sev, scope = "ai_disruption", 5.0, "global"
        elif any(w in q for w in ["game", "gaming", "esports", "fortnite", "valorant", "steam", "epic", "playstation", "xbox", "nintendo"]):
            etype, sev, scope = "gaming_industry", 4.0, "global"
        elif any(w in q for w in ["movie", "film", "streaming", "netflix", "disney", "entertainment", "music", "spotify"]):
            etype, sev, scope = "entertainment_industry", 4.0, "global"
        elif any(w in q for w in ["social media", "twitter", "facebook", "instagram", "tiktok", "youtube"]):
            etype, sev, scope = "social_media_event", 4.0, "global"
        elif any(w in q for w in ["sport", "olympics", "fifa", "nfl", "nba", "cricket", "formula"]):
            etype, sev, scope = "sports_disruption", 3.0, "global"
        elif any(w in q for w in ["bankrupt", "collapse", "shutdown", "shut down", "close", "goes down", "fails"]):
            etype, sev, scope = "corporate_collapse", 5.0, "global"
        elif any(w in q for w in ["nuclear", "radiation", "meltdown", "reactor"]):
            etype, sev, scope = "nuclear_incident", 9.0, "global"
        elif any(w in q for w in ["climate", "warming", "carbon", "emission", "drought", "wildfire"]):
            etype, sev, scope = "climate_event", 6.0, "global"
        elif any(w in q for w in ["food", "famine", "hunger", "crop", "grain", "wheat"]):
            etype, sev, scope = "food_crisis", 7.0, "global"
        elif any(w in q for w in ["strike", "labor", "union", "worker", "walkout"]):
            etype, sev, scope = "labor_strike", 4.0, "regional"
        elif any(w in q for w in ["space", "satellite", "nasa", "spacex", "asteroid", "orbit"]):
            etype, sev, scope = "space_event", 5.0, "global"
        elif any(w in q for w in ["terrorism", "terrorist", "bombing", "9/11", "extremis"]):
            etype, sev, scope = "terrorism", 8.0, "global"
        else:
            etype, sev, scope = "geopolitical_event", 5.0, "regional"

        return ParsedScenario(
            event_type=etype,
            title=query[:80],
            description=query,
            location=self._extract_location(q) or "Unknown",
            countries=[],
            actors=[],
            severity_estimate=sev,
            estimated_timeline="medium_term",
            economic_scope=scope,
            uncertainty_factors=["Deterministic analysis: high uncertainty"],
            original_query=query,
        )

    def _extract_location(self, q: str) -> Optional[str]:
        countries = [
            "russia", "china", "usa", "united states", "ukraine", "iran", "iraq",
            "north korea", "israel", "saudi arabia", "india", "pakistan", "afghanistan",
            "venezuela", "turkey", "syria", "taiwan", "japan", "germany", "france",
            "united kingdom", "uk", "eu", "europe", "middle east", "asia", "africa",
            "latin america", "south america", "australia", "canada", "mexico",
        ]
        for c in countries:
            if c in q:
                return c.title()
        return None
