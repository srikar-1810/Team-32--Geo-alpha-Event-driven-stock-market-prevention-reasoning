from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from app.logging_config import get_logger
from app.services.historical.event_mapper import SECTOR_KEYWORD_MAP
from app.services.historical.market_collector import SECTOR_TICKER_MAP
from app.services.simulation.models import InferredSector, InferredStock, ParsedScenario
from app.services.tiingo.client import SECTOR_ETF_MAP

logger = get_logger(__name__)

SECTOR_INFERENCE_SYSTEM = """You are a senior geopolitical macro strategist and sector analyst (e.g., at Goldman Sachs or Bridgewater Associates).
Analyze the hypothetical geopolitical event and infer exactly which financial sectors and specific stocks will be impacted.
Consider first, second, and third-order effects, including:
- Supply chain disruptions and chokepoints
- Commodity price shocks (oil, gas, metals, agricultural)
- Regulatory and policy changes
- Currency and FX implications
- Interest rate and central bank responses
- Consumer behavior shifts
- Capital flow reallocation
- Technology disruption and cybersecurity
- Insurance and reinsurance exposure
- Regional banking and credit exposure

Provide AT LEAST 10-15 sectors and 25-30 specific stock tickers with deep reasoning.
Include both DIRECT impacts and INDIRECT second/third-order effects.
For each stock, explain the specific business exposure (e.g., revenue %, geographic presence, supply chain dependency).

Output ONLY valid JSON with this structure:
{
  "sectors": [
    {
      "sector_name": "string",
      "impact_direction": "bullish|bearish|neutral",
      "impact_magnitude": 0.0-1.0,
      "confidence": 0.0-1.0,
      "reasoning": "string (2-3 sentences of deep macro reasoning with specific data points)"
    }
  ],
  "stocks": [
    {
      "ticker": "string",
      "company_name": "string",
      "exposure_type": "direct|indirect|supply_chain|competitive|beneficiary",
      "relevance_score": 0.0-1.0,
      "reasoning": "string (specific business exposure explanation)"
    }
  ]
}"""


class SectorStockInferrer:
    """Infers affected sectors and stocks from a hypothetical scenario."""

    async def infer(
        self, scenario: ParsedScenario, top_k_sectors: int = 15, top_k_stocks: int = 30,
    ) -> Tuple[List[InferredSector], List[InferredStock]]:
        keyword_sectors = self._keyword_match(scenario)
        llm_sectors, llm_stocks = await self._llm_infer(scenario)

        merged_sectors = self._merge_sectors(keyword_sectors, llm_sectors, top_k_sectors)
        merged_stocks = self._merge_stocks(llm_stocks, merged_sectors, top_k_stocks)

        return merged_sectors, merged_stocks

    def _keyword_match(self, scenario: ParsedScenario) -> List[InferredSector]:
        text = f"{scenario.title} {scenario.description} {scenario.event_type} {scenario.location}".lower()
        text += f" {' '.join(scenario.countries).lower()} {' '.join(scenario.actors).lower()}"

        matched_sectors: List[InferredSector] = []
        for etf, keywords in SECTOR_KEYWORD_MAP.items():
            matched_kws = [kw for kw in keywords if kw.lower() in text]
            if matched_kws:
                sector_name = SECTOR_ETF_MAP.get(etf, etf)
                magnitude = min(1.0, len(matched_kws) / 5.0)
                direction = self._infer_direction(scenario.event_type, etf)
                matched_sectors.append(InferredSector(
                    sector_name=sector_name,
                    etf_ticker=etf,
                    impact_direction=direction,
                    impact_magnitude=magnitude,
                    confidence=0.5 + magnitude * 0.3,
                    reasoning=f"Keyword match: {', '.join(matched_kws[:4])}",
                ))

        return matched_sectors

    async def _llm_infer(self, scenario: ParsedScenario) -> Tuple[List[Dict], List[Dict]]:
        from app.utils.llm_client import create_llm_client
        from app.config import settings

        prompt = (
            f"Hypothetical geopolitical event:\n"
            f"Title: {scenario.title}\n"
            f"Description: {scenario.description}\n"
            f"Type: {scenario.event_type}\n"
            f"Location: {scenario.location}\n"
            f"Countries: {', '.join(scenario.countries)}\n"
            f"Actors: {', '.join(scenario.actors)}\n"
            f"Severity: {scenario.severity_estimate}/10\n"
            f"Economic Scope: {scenario.economic_scope}\n\n"
            f"Infer affected financial sectors (ETF tickers) and specific stock tickers."
        )

        try:
            client = create_llm_client()
            response = await client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": SECTOR_INFERENCE_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            text = response.choices[0].message.content or "{}"
            
            # Robust JSON extraction
            try:
                # 1. Try stripping markdown blocks first
                clean_text = re.sub(r'```json\s*|\s*```', '', text).strip()
                # 2. Try to find the first { and last } to handle extra conversational text
                match = re.search(r'\{.*\}', clean_text, re.DOTALL)
                if match:
                    data = json.loads(match.group())
                else:
                    data = json.loads(clean_text)
            except Exception:
                # Fallback to simple loads if regex fails
                data = json.loads(text)

            return data.get("sectors", []), data.get("stocks", [])
        except Exception as e:
            logger.warning("LLM sector inference failed: %s", e)
            return [], []

    def _merge_sectors(
        self, keyword_sectors: List[InferredSector],
        llm_sectors: List[Dict], top_k: int,
    ) -> List[InferredSector]:
        merged: Dict[str, InferredSector] = {}

        for ks in keyword_sectors:
            merged[ks.etf_ticker] = ks

        for ls in llm_sectors:
            name = ls.get("sector_name", "")
            etf = self._sector_to_etf(name)
            if etf not in merged:
                merged[etf] = InferredSector(
                    sector_name=name,
                    etf_ticker=etf,
                    impact_direction=ls.get("impact_direction", "neutral"),
                    impact_magnitude=float(ls.get("impact_magnitude", 0.5)),
                    confidence=float(ls.get("confidence", 0.5)),
                    reasoning=ls.get("reasoning", ""),
                )
            else:
                existing = merged[etf]
                existing.impact_magnitude = max(existing.impact_magnitude, float(ls.get("impact_magnitude", 0.5)))
                existing.confidence = max(existing.confidence, float(ls.get("confidence", 0.5)))
                if ls.get("reasoning"):
                    existing.reasoning += f" | LLM: {ls['reasoning']}"

        sectors = list(merged.values())
        sectors.sort(key=lambda s: s.impact_magnitude, reverse=True)
        return sectors[:top_k]

    def _merge_stocks(
        self, llm_stocks: List[Dict],
        sectors: List[InferredSector], top_k: int,
    ) -> List[InferredStock]:
        stock_map: Dict[str, InferredStock] = {}

        for tickers in SECTOR_TICKER_MAP.values():
            for t in tickers:
                for sector in sectors:
                    if t in SECTOR_TICKER_MAP.get(sector.etf_ticker, []):
                        stock_map[t] = InferredStock(
                            ticker=t,
                            company_name="",
                            sector=sector.sector_name,
                            etf_ticker=sector.etf_ticker,
                            relevance_score=sector.impact_magnitude * 0.7,
                            exposure_type="sector_exposure",
                            reasoning=f"Sector {sector.sector_name} impacted ({sector.impact_direction})",
                        )

        for ls in llm_stocks:
            ticker = ls.get("ticker", "").upper()
            if ticker and ticker not in stock_map:
                stock_map[ticker] = InferredStock(
                    ticker=ticker,
                    company_name=ls.get("company_name", ""),
                    sector="",
                    etf_ticker=self._ticker_to_etf(ticker),
                    relevance_score=float(ls.get("relevance_score", 0.5)),
                    exposure_type=ls.get("exposure_type", "direct"),
                    reasoning=ls.get("reasoning", "LLM identified"),
                )

        stocks = list(stock_map.values())
        stocks.sort(key=lambda s: s.relevance_score, reverse=True)
        return stocks[:top_k]

    def _infer_direction(self, event_type: str, etf: str) -> str:
        bullish_map: Dict[str, List[str]] = {
            "war": ["XLE", "XLI", "XLF", "GLD", "USO"],
            "sanctions": ["XLE", "XLE", "GLD", "USO"],
            "natural_disaster": ["XLB", "XLI", "XLU"],
            "cyberattack": ["XLK", "XLC"],
            "pandemic": ["XLV", "XLK"],
            "election": ["XLF", "XLV", "XLC"],
        }
        bearish_map: Dict[str, List[str]] = {
            "war": ["XLY", "XLP", "XLU"],
            "sanctions": ["XLY", "XLK", "XLC"],
            "natural_disaster": ["XLY", "XLP"],
            "financial_crisis": ["XLF", "XLY", "XLRE"],
            "trade_dispute": ["XLI", "XLB", "XLY"],
        }

        if etf in bullish_map.get(event_type, []):
            return "bullish"
        if etf in bearish_map.get(event_type, []):
            return "bearish"
        return "neutral"

    def _sector_to_etf(self, name: str) -> str:
        reverse_map = {v.lower(): k for k, v in SECTOR_ETF_MAP.items()}
        return reverse_map.get(name.lower(), name)

    def _ticker_to_etf(self, ticker: str) -> str:
        for etf, tickers in SECTOR_TICKER_MAP.items():
            if ticker.upper() in tickers:
                return etf
        return ""
