from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.logging_config import get_logger
from app.models.agent_state import AgentExecution
from app.models.geopol_event import GeoPolEvent
from app.models.market_data import MarketDataPoint, MarketImpactAssessment, SectorExposure
from app.models.sentiment import SentimentAggregate, SentimentData

logger = get_logger(__name__)


class IngestionNormalizer:
    """Normalizes raw ingested data from all sources into standardized domain models."""

    @staticmethod
    def normalize_gdelt_article(raw: Dict[str, Any]) -> Optional[GeoPolEvent]:
        try:
            from app.services.gdelt.parser import GDELTParser
            return GDELTParser.parse_article(raw)
        except Exception as e:
            logger.warning("GDELT article normalization failed: %s", e)
            return None

    @staticmethod
    def normalize_gdelt_event(raw: Dict[str, Any]) -> Optional[GeoPolEvent]:
        try:
            from app.services.gdelt.parser import GDELTParser
            return GDELTParser.parse_event(raw)
        except Exception as e:
            logger.warning("GDELT event normalization failed: %s", e)
            return None

    @staticmethod
    def normalize_reddit_post(raw: Dict[str, Any]) -> Optional[SentimentData]:
        try:
            from app.services.reddit.analyzer import SentimentAnalyzer
            return SentimentAnalyzer.analyze_post(raw)
        except Exception as e:
            logger.warning("Reddit post normalization failed: %s", e)
            return None

    @staticmethod
    def normalize_market_data(raw: Dict[str, Any], ticker: str, source: str = "tiingo") -> Optional[MarketDataPoint]:
        try:
            if source == "tiingo":
                from app.services.tiingo.client import TiingoClient
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                client = TiingoClient()
                return loop.run_until_complete(client.to_market_model(raw, ticker))
            else:
                return MarketDataPoint(
                    ticker=ticker,
                    date=datetime.fromisoformat(raw.get("date", "")).date()
                    if raw.get("date") else datetime.now(timezone.utc).date(),
                    open_price=float(raw.get("open", raw.get("open_price", 0.0))),
                    high_price=float(raw.get("high", raw.get("high_price", 0.0))),
                    low_price=float(raw.get("low", raw.get("low_price", 0.0))),
                    close_price=float(raw.get("close", raw.get("close_price", 0.0))),
                    volume=int(raw.get("volume", 0)),
                    adj_close=float(raw.get("adjClose", raw.get("adj_close", 0))) or None,
                    change_pct=float(raw.get("changePct", raw.get("change_pct", 0.0))) or None,
                    source=source,
                    raw_data=raw,
                )
        except Exception as e:
            logger.warning("Market data normalization failed for %s: %s", ticker, e)
            return None

    @staticmethod
    def normalize_yahoo_quote(raw: Dict[str, Any], ticker: str) -> Optional[MarketDataPoint]:
        try:
            return MarketDataPoint(
                ticker=ticker,
                date=datetime.now(timezone.utc).date(),
                open_price=float(raw.get("open", 0.0)),
                high_price=float(raw.get("high", 0.0)),
                low_price=float(raw.get("low", 0.0)),
                close_price=float(raw.get("close", raw.get("regularMarketPrice", 0.0))),
                volume=int(raw.get("volume", raw.get("regularMarketVolume", 0))),
                source="yahoo",
                raw_data=raw,
            )
        except Exception as e:
            logger.warning("Yahoo quote normalization failed for %s: %s", ticker, e)
            return None

    @staticmethod
    def normalize_sentiment_aggregate(
        posts: List[SentimentData],
        query: str = "",
        source: str = "reddit",
    ) -> SentimentAggregate:
        try:
            from app.services.reddit.analyzer import SentimentAnalyzer
            return SentimentAnalyzer.aggregate(posts, query=query, source=source)
        except Exception as e:
            logger.warning("Sentiment aggregate normalization failed: %s", e)
            return SentimentAggregate(
                query=query,
                source=source,
                overall_score=0.0,
                confidence=0.0,
                volume=len(posts),
                top_keywords=[],
                top_posts=[],
                period_start=None,
                period_end=None,
            )

    @staticmethod
    def compute_sector_exposure(
        ticker_sector_map: Dict[str, str],
        prices: Dict[str, List[MarketDataPoint]],
    ) -> List[SectorExposure]:
        exposures: Dict[str, SectorExposure] = {}

        for ticker, sector in ticker_sector_map.items():
            points = prices.get(ticker, [])
            if not points:
                continue
            closes = [p.close_price for p in points[-20:]]
            if len(closes) < 5:
                continue

            returns = []
            for i in range(1, len(closes)):
                if closes[i - 1] > 0:
                    returns.append((closes[i] - closes[i - 1]) / closes[i - 1])

            import statistics as stat
            vol = stat.stdev(returns) if len(returns) > 1 else 0.0

            if sector not in exposures:
                exposures[sector] = SectorExposure(
                    sector=sector,
                    tickers=[],
                    exposure_pct=0.0,
                    volatility=round(vol, 6),
                    beta=1.0,
                    last_updated=datetime.now(timezone.utc),
                )
            exposures[sector].tickers.append(ticker)

        return list(exposures.values())

    @staticmethod
    def build_impact_assessment(
        event: GeoPolEvent,
        sector_impacts: Dict[str, float],
        affected_tickers: Dict[str, List[str]],
        confidence: float = 0.5,
    ) -> MarketImpactAssessment:
        overall = sum(sector_impacts.values()) / max(len(sector_impacts), 1)

        return MarketImpactAssessment(
            event_id=event.id,
            overall_impact_score=round(overall, 4),
            affected_sectors=[
                {
                    "sector": sector,
                    "impact_score": score,
                    "reasoning": f"Impact derived from event: {event.title[:100]}",
                }
                for sector, score in sector_impacts.items()
            ],
            top_impacted_stocks=[
                {"sector": sector, "tickers": tickers}
                for sector, tickers in affected_tickers.items()
            ],
            volatility_forecast=[
                {
                    "sector": sector,
                    "forecast_volatility": round(abs(score) * 0.3, 4),
                }
                for sector, score in sector_impacts.items()
            ],
            confidence=confidence,
            model_used="gdelt+market_analysis",
            generated_at=datetime.now(timezone.utc),
        )
