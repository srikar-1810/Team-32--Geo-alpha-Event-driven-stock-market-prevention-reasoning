from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from app.services.workflow.base import EnhancedAgentNode
from app.services.workflow.prompts import MARKET_STRATEGIST_SYSTEM
from app.services.workflow.state import WorkflowState
from app.services.workflow.tools import AgentTools


class MarketStrategistNode(EnhancedAgentNode):
    """Agent node: infers sector and stock impacts from all upstream analyses."""

    def __init__(self, tools: Optional[AgentTools] = None) -> None:
        super().__init__(
            agent_id="market-strategist",
            agent_name="Market Strategist Agent",
        )
        self._tools_inst = tools or AgentTools()

    def _goals(self) -> str:
        return (
            "Synthesize geopolitical intelligence, social sentiment, and historical "
            "analogues into sector and stock-level impact assessments. "
            "Generate a sector impact matrix, stock picks, portfolio "
            "implications, and hedging recommendations."
        )

    async def __call__(self, state: WorkflowState) -> WorkflowState:
        start = time.perf_counter()
        self._log_step(state, "START")

        query = state.get("query", "")
        tickers = state.get("tickers", [])
        news = state.get("news_analysis", {}) or {}
        sentiment = state.get("sentiment_analysis", {}) or {}
        historical = state.get("historical_analysis", {}) or {}

        sectors_from_news = [
            s.get("sector", "") for s in (news.get("primary_sectors_impacted") or [])
        ]

        sector_etfs = self._map_sectors_to_etfs(sectors_from_news)
        all_sector_tickers = list(sector_etfs.keys())

        sector_prices = await self._tools_inst.get_sector_prices(
            tickers=all_sector_tickers, days_back=30,
        )

        stock_data = {}
        if tickers:
            stock_data = await self._tools_inst.get_stock_data(tickers, days_back=30)

        macro_data = await self._tools_inst.get_market_macro()

        state["sector_data"] = sector_prices
        state["stock_data"] = stock_data

        historical_raw = historical.get("_raw_analogues", [])
        analogue_sectors: Dict[str, int] = {}
        analogue_bullish: Dict[str, int] = {}
        analogue_bearish: Dict[str, int] = {}
        for a in historical_raw:
            secs = a.get("sectors", "")
            for s in secs.split(","):
                s = s.strip()
                if s:
                    analogue_sectors[s] = analogue_sectors.get(s, 0) + 1
            for t in (a.get("bullish_tickers", "") or "").split(","):
                t = t.strip()
                if t:
                    analogue_bullish[t] = analogue_bullish.get(t, 0) + 1
            for t in (a.get("bearish_tickers", "") or "").split(","):
                t = t.strip()
                if t:
                    analogue_bearish[t] = analogue_bearish.get(t, 0) + 1

        top_analogue_sectors = sorted(analogue_sectors, key=analogue_sectors.get, reverse=True)[:5]
        top_analogue_bullish = sorted(analogue_bullish, key=analogue_bullish.get, reverse=True)[:5]
        top_analogue_bearish = sorted(analogue_bearish, key=analogue_bearish.get, reverse=True)[:5]

        news_sectors_text = "\n".join(
            f"  {s.get('sector', '?')}: {s.get('impact_direction', 'neutral')} "
            f"(conf={s.get('confidence', 0):.2f})"
            for s in (news.get("primary_sectors_impacted") or [])
        )

        historical_reactions = historical.get("_market_reactions", {})

        user_prompt = (
            f"Synthesize all upstream analyses into sector and stock impact assessments.\n\n"
            f"Event: {query}\n"
            f"Tickers: {', '.join(tickers)}\n\n"
            f"News-indicated sector impacts:\n{news_sectors_text or '  None specified'}\n\n"
            f"Social sentiment: {sentiment.get('overall_sentiment', 'neutral')} "
            f"(score={sentiment.get('sentiment_score', 0):.2f})\n"
            f"  Key narratives: {sentiment.get('key_narratives', [])}\n\n"
            f"Historical analogue sector frequency: {top_analogue_sectors}\n"
            f"Historical analogue bullish tickers: {top_analogue_bullish}\n"
            f"Historical analogue bearish tickers: {top_analogue_bearish}\n"
            f"Historical avg volatility change: {historical_reactions.get('avg_volatility_change_pct', 'N/A')}%\n"
            f"Historical avg 5d return: {historical_reactions.get('avg_market_return_5d', 'N/A')}%\n\n"
            f"Available sector price data: {list(sector_prices.keys())}\n"
            f"Available stock data: {list(stock_data.keys())}\n\n"
            f"Macro context available: {bool(macro_data)}"
        )

        llm_output, fallback_used, model_used = await self._call_llm(
            system_prompt=MARKET_STRATEGIST_SYSTEM,
            user_prompt=user_prompt,
            output_schema="JSON object with market_regime_assessment, sector_impact_matrix, stock_impact_picks, portfolio_implications, hedging_recommendations, macro_tail_risks",
        )

        parsed = self._extract_json_from_output(llm_output)
        if parsed is None:
            parsed = self._deterministic_fallback(
                sectors_from_news, top_analogue_bullish, top_analogue_bearish, tickers,
            )

        state["market_analysis"] = parsed

        elapsed = (time.perf_counter() - start) * 1000
        ctx = self._build_agent_context(state, parsed, execution_time_ms=elapsed, fallback_used=fallback_used, model_used=model_used)
        state.setdefault("agent_contexts", {})[self.agent_id] = ctx
        self._log_step(state, "COMPLETE", f"{len(parsed.get('sector_impact_matrix', []))} sectors, {elapsed:.0f}ms")
        return state

    def _map_sectors_to_etfs(self, sectors: List[str]) -> Dict[str, str]:
        mapping = {
            "financial": "XLF", "energy": "XLE", "technology": "XLK",
            "healthcare": "XLV", "industrial": "XLI", "materials": "XLB",
            "utilities": "XLU", "consumer_cyclical": "XLY", "consumer_defensive": "XLP",
            "real_estate": "XLRE", "communication": "XLC",
        }
        return {ticker: name for name, ticker in mapping.items() if name in sectors}

    def _deterministic_fallback(
        self, sectors: List[str], bullish: List[str], bearish: List[str], tickers: List[str],
    ) -> Dict[str, Any]:
        matrix = []
        for s in sectors[:5]:
            matrix.append({
                "sector": s,
                "etf_ticker": self._map_sectors_to_etfs([s]).get(s, ""),
                "impact_direction": "neutral",
                "impact_magnitude": 0.3,
                "confidence": 0.3,
                "time_horizon": "medium_term",
                "reasoning": "LLM unavailable, estimated from news classification",
                "key_levels_to_watch": [],
            })
        return {
            "market_regime_assessment": "Unable to assess (deterministic fallback)",
            "sector_impact_matrix": matrix,
            "stock_impact_picks": [
                {"ticker": t, "direction": "watch", "conviction": "low",
                 "reasoning": "LLM unavailable", "catalysts": []}
                for t in tickers[:5]
            ],
            "portfolio_implications": "See sector matrix above",
            "hedging_recommendations": ["Monitor volatility"],
            "macro_tail_risks": ["Unable to assess"],
        }
