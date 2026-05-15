from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.logging_config import get_logger
from app.services.chroma.client import ChromaClient
from app.services.chroma.embeddings import EmbeddingService
from app.services.gdelt.client import GDELTClient
from app.services.gdelt.parser import GDELTParser
from app.services.historical.models import HistoricalMarketImpact
from app.services.historical.orchestrator import HistoricalOrchestrator
from app.services.rag.historical_rag import HistoricalRAGService
from app.services.reddit.analyzer import SentimentAnalyzer
from app.services.reddit.client import RedditClient
from app.services.tiingo.client import TiingoClient, SECTOR_ETF_MAP
from app.services.yahoo.client import YahooFinanceClient

logger = get_logger(__name__)


class AgentTools:
    """Shared tools available to all workflow agents."""

    def __init__(self) -> None:
        self._gdelt: Optional[GDELTClient] = None
        self._reddit: Optional[RedditClient] = None
        self._analyzer: Optional[SentimentAnalyzer] = None
        self._tiingo: Optional[TiingoClient] = None
        self._yahoo: Optional[YahooFinanceClient] = None
        self._chroma: Optional[ChromaClient] = None
        self._embeddings: Optional[EmbeddingService] = None
        self._historical_rag: Optional[HistoricalRAGService] = None
        self._orchestrator: Optional[HistoricalOrchestrator] = None

    # ── Lazy initialization ──

    @property
    def gdelt(self) -> GDELTClient:
        if self._gdelt is None:
            self._gdelt = GDELTClient()
        return self._gdelt

    @property
    def reddit(self) -> RedditClient:
        if self._reddit is None:
            self._reddit = RedditClient()
        return self._reddit

    @property
    def analyzer(self) -> SentimentAnalyzer:
        if self._analyzer is None:
            self._analyzer = SentimentAnalyzer()
        return self._analyzer

    @property
    def tiingo(self) -> TiingoClient:
        if self._tiingo is None:
            self._tiingo = TiingoClient()
        return self._tiingo

    @property
    def yahoo(self) -> YahooFinanceClient:
        if self._yahoo is None:
            self._yahoo = YahooFinanceClient()
        return self._yahoo

    @property
    def chroma(self) -> ChromaClient:
        if self._chroma is None:
            self._chroma = ChromaClient()
        return self._chroma

    @property
    def embeddings(self) -> EmbeddingService:
        if self._embeddings is None:
            self._embeddings = EmbeddingService()
        return self._embeddings

    @property
    def historical_rag(self) -> HistoricalRAGService:
        if self._historical_rag is None:
            self._historical_rag = HistoricalRAGService(
                chroma=self.chroma, embeddings=self.embeddings,
            )
        return self._historical_rag

    @property
    def historical_orchestrator(self) -> HistoricalOrchestrator:
        if self._orchestrator is None:
            self._orchestrator = HistoricalOrchestrator()
        return self._orchestrator

    # ── News Intelligence Tools ──

    async def fetch_gdelt_events(
        self,
        query: str,
        max_records: int = 25,
        days_back: int = 7,
    ) -> List[Dict[str, Any]]:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days_back)
        try:
            articles = await self.gdelt.fetch_article_list(
                query=query, start_date=start, end_date=end, max_records=max_records,
            )
            parser = GDELTParser()
            return [parser.parse_article(a).to_dict() if parser.parse_article(a) else a for a in articles]
        except Exception as e:
            logger.warning("GDELT fetch failed: %s", e)
            return []

    async def fetch_gdelt_events_cameo(
        self,
        query: str,
        max_records: int = 25,
        days_back: int = 7,
    ) -> List[Dict[str, Any]]:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days_back)
        try:
            events = await self.gdelt.fetch_events(
                query=query, start_date=start, end_date=end, max_records=max_records,
            )
            return events
        except Exception as e:
            logger.warning("GDELT Event fetch failed: %s", e)
            return []

    # ── Social Sentiment Tools ──

    async def fetch_reddit_sentiment(
        self,
        query: str,
        subreddits: Optional[List[str]] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        try:
            posts = await self.reddit.fetch_multiple_subreddits(
                subreddits=subreddits, limit=limit,
            )
            analyzed = [self.analyzer.analyze_post(p) for p in posts]
            aggregate = self.analyzer.aggregate(analyzed, query=query)
            return {
                "posts_analyzed": len(analyzed),
                "overall_score": aggregate.overall_score,
                "confidence": aggregate.confidence,
                "distribution": aggregate.distribution,
                "volume": aggregate.volume,
                "top_keywords": aggregate.top_keywords[:15],
                "signal": self._generate_sentiment_signal(aggregate),
            }
        except Exception as e:
            logger.warning("Reddit sentiment fetch failed: %s", e)
            return {
                "posts_analyzed": 0,
                "overall_score": 0.0,
                "confidence": 0.0,
                "distribution": {},
                "volume": 0,
                "top_keywords": [],
                "signal": "neutral",
            }

    @staticmethod
    def _generate_sentiment_signal(agg: Any) -> str:
        if agg.overall_score > 0.3 and agg.confidence > 0.5:
            return "bullish"
        elif agg.overall_score < -0.3 and agg.confidence > 0.5:
            return "bearish"
        elif abs(agg.overall_score) <= 0.3 and agg.volume > 50:
            return "neutral_high_volume"
        return "neutral"

    # ── Historical RAG Tools ──

    async def query_historical_rag(
        self,
        query: str,
        top_k: int = 10,
    ) -> Dict[str, Any]:
        try:
            results = await self.historical_rag.retrieve_similar(
                query_text=query, top_k=top_k,
            )
            market_reactions = self.historical_rag.extract_market_reactions(results)

            processed = []
            for r in results:
                meta = r.get("metadata", {})
                confidence = self.historical_rag.compute_confidence(r["similarity"], meta)
                processed.append({
                    "event_id": r["event_id"],
                    "event_title": meta.get("event_title", ""),
                    "event_type": meta.get("event_type", ""),
                    "event_date": meta.get("event_date", ""),
                    "similarity": r["similarity"],
                    "sectors": meta.get("sectors", ""),
                    "bullish_tickers": meta.get("bullish_tickers", ""),
                    "bearish_tickers": meta.get("bearish_tickers", ""),
                    "confidence": confidence,
                })

            return {
                "total_results": len(processed),
                "results": processed,
                "market_reactions": market_reactions,
            }
        except Exception as e:
            logger.warning("Historical RAG query failed: %s", e)
            return {"total_results": 0, "results": [], "market_reactions": {}}

    async def get_historical_stats(self) -> Dict[str, Any]:
        try:
            return await self.historical_orchestrator.get_stats()
        except Exception as e:
            logger.warning("Historical stats failed: %s", e)
            return {}

    # ── Market Data Tools ──

    async def get_sector_prices(
        self,
        tickers: Optional[List[str]] = None,
        days_back: int = 30,
    ) -> Dict[str, Any]:
        targets = tickers or list(SECTOR_ETF_MAP.keys())[:10]
        end = date.today()
        start = end - timedelta(days=days_back + 10)
        try:
            prices = await self.tiingo.get_sector_etf_prices(start_date=start, end_date=end)
            return {t: [{"date": str(p.date), "close": p.close_price} for p in pts[-30:]]
                    for t, pts in prices.items() if t in targets}
        except Exception as e:
            logger.warning("Sector price fetch failed: %s", e)
            return {}

    async def get_stock_data(
        self,
        tickers: List[str],
        days_back: int = 30,
    ) -> Dict[str, Any]:
        end = date.today()
        start = end - timedelta(days=days_back + 10)
        result = {}
        for ticker in tickers:
            try:
                points = await self.yahoo.get_market_data_points(ticker, start, end)
                if points:
                    result[ticker] = [
                        {"date": str(p.date), "close": p.close_price, "volume": p.volume}
                        for p in points[-30:]
                    ]
            except Exception:
                continue
        return result

    async def get_market_macro(self) -> Dict[str, float]:
        from app.services.historical.enrichment import MacroCollector
        mc = MacroCollector()
        try:
            return await mc.collect_macro_context(date.today(), window_days=5)
        except Exception as e:
            logger.warning("Macro data fetch failed: %s", e)
            return {}

    # ── Utility Tools ──

    async def close_all(self) -> None:
        for client_name in ["_gdelt", "_reddit", "_tiingo", "_yahoo", "_chroma"]:
            client = getattr(self, client_name, None)
            if client and hasattr(client, "close"):
                try:
                    await client.close()
                except Exception:
                    pass
