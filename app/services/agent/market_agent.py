from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from app.logging_config import get_logger
from app.models.market_data import MarketDataPoint, MarketImpactAssessment
from app.services.agent.base import BaseAgent
from app.services.tiingo.client import TiingoClient


class MarketAnalystAgent(BaseAgent):
    """Analyzes market data and assesses geopolitical impact on stocks/sectors."""

    def __init__(self, tiingo_client: Optional[TiingoClient] = None) -> None:
        super().__init__(
            agent_id="market-agent",
            name="Market Analyst",
        )
        self.tiingo = tiingo_client or TiingoClient()

    async def run(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        tickers = input_data.get("tickers", [])
        event_description = input_data.get("event_description", "")
        days_back = input_data.get("days_back", 30)

        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)

        market_data: Dict[str, List[MarketDataPoint]] = {}
        for ticker in tickers:
            try:
                raw = await self.tiingo.get_daily_prices(
                    ticker=ticker,
                    start_date=start_date,
                    end_date=end_date,
                )
                market_data[ticker] = [
                    await self.tiingo.to_market_model(r, ticker) for r in raw
                ]
            except Exception as e:
                self.logger.warning("Failed to fetch data for %s: %s", ticker, e)

        analysis_prompt = (
            f"Market impact analysis for event:\n{event_description}\n\n"
            f"Market data summary:\n{self._summarize_market_data(market_data)}\n\n"
            f"Provide:\n"
            f"1. Impact assessment on each ticker\n"
            f"2. Volatility analysis\n"
            f"3. Support/resistance levels\n"
            f"4. Trading recommendations"
        )

        llm_output = await self._call_llm(
            system_prompt="You are a senior market analyst specializing in geopolitical event impact.",
            user_prompt=analysis_prompt,
        )

        self._add_to_memory("user", str(input_data))
        self._add_to_memory("assistant", llm_output)

        return {
            "agent": self.agent_id,
            "status": "completed",
            "tickers_analyzed": tickers,
            "market_data_summary": self._compute_summary(market_data),
            "analysis": llm_output,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _summarize_market_data(self, data: Dict[str, List[MarketDataPoint]]) -> str:
        lines = []
        for ticker, points in data.items():
            if not points:
                continue
            closes = [p.close_price for p in points]
            changes = [p.change_pct for p in points if p.change_pct is not None]
            lines.append(
                f"{ticker}: close_range=[{min(closes):.2f}-{max(closes):.2f}], "
                f"avg_change={sum(changes)/len(changes):.2% if changes else 'N/A'}, "
                f"volatility={self._volatility(closes):.2%}"
            )
        return "\n".join(lines)

    def _compute_summary(self, data: Dict[str, List[MarketDataPoint]]) -> Dict[str, Any]:
        summary = {}
        for ticker, points in data.items():
            if not points:
                continue
            closes = [p.close_price for p in points]
            volumes = [p.volume for p in points]
            summary[ticker] = {
                "start_price": closes[0],
                "end_price": closes[-1],
                "high": max(closes),
                "low": min(closes),
                "avg_volume": sum(volumes) / len(volumes),
                "volatility": self._volatility(closes),
                "return_pct": ((closes[-1] - closes[0]) / closes[0]) * 100,
            }
        return summary

    @staticmethod
    def _volatility(prices: List[float]) -> float:
        if len(prices) < 2:
            return 0.0
        returns = [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices))]
        import statistics
        return statistics.stdev(returns) if returns else 0.0
