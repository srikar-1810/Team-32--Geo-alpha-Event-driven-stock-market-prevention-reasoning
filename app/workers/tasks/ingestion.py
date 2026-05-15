from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from app.logging_config import get_logger
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(bind=True, max_retries=3, soft_time_limit=300)
def ingest_gdelt_events(self, query: str = "conflict OR election OR crisis OR sanctions") -> Dict[str, Any]:
    logger.info("Starting GDELT ingestion task: query='%s'", query)
    try:
        import asyncio
        from app.services.gdelt.client import GDELTClient
        from app.services.gdelt.parser import GDELTParser

        async def _ingest():
            from app.services.ingestion.storage import geopol_storage
            async with GDELTClient() as client:
                raw_events = await client.fetch_events(query=query, max_records=250)
                events = GDELTParser.batch_parse_events(raw_events)
                
                if events:
                    await geopol_storage.save_events(events)
                    
                logger.info("Ingested and saved %d GDELT events", len(events))
                return {
                    "status": "success",
                    "events_count": len(events),
                    "query": query,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_ingest())

    except Exception as e:
        logger.error("GDELT ingestion failed: %s", e)
        self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=3, soft_time_limit=120)
def ingest_reddit_sentiment(self, subreddits: str = "") -> Dict[str, Any]:
    logger.info("Starting Reddit sentiment ingestion task")
    try:
        import asyncio
        from app.services.reddit.analyzer import SentimentAnalyzer
        from app.services.reddit.client import RedditClient

        async def _ingest():
            async with RedditClient() as client:
                targets = [s.strip() for s in subreddits.split(",")] if subreddits else None
                posts = await client.fetch_multiple_subreddits(subreddits=targets, limit=100)
                analyzer = SentimentAnalyzer()
                analyzed = [analyzer.analyze_post(p) for p in posts]
                logger.info("Ingested %d Reddit posts", len(analyzed))
                return {
                    "status": "success",
                    "posts_count": len(analyzed),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_ingest())

    except Exception as e:
        logger.error("Reddit ingestion failed: %s", e)
        self.retry(exc=e, countdown=60)


@celery_app.task(bind=True, max_retries=3, soft_time_limit=120)
def ingest_market_data(self, tickers: str = "SPY,QQQ,IWM,EEM,XLF,XLE,XLK,XLV") -> Dict[str, Any]:
    logger.info("Starting market data ingestion: tickers='%s'", tickers)
    try:
        import asyncio
        from datetime import date, timedelta
        from app.services.tiingo.client import TiingoClient

        async def _ingest():
            ticker_list = [t.strip() for t in tickers.split(",")]
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            results = {}

            async with TiingoClient() as client:
                for ticker in ticker_list:
                    try:
                        data = await client.get_daily_prices(
                            ticker=ticker,
                            start_date=start_date,
                            end_date=end_date,
                        )
                        results[ticker] = len(data)
                    except Exception as e:
                        logger.warning("Failed to ingest %s: %s", ticker, e)
                        results[ticker] = 0

            logger.info("Market data ingestion complete: %s", results)
            return {
                "status": "success",
                "tickers_count": len(ticker_list),
                "results": results,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_ingest())

    except Exception as e:
        logger.error("Market data ingestion failed: %s", e)
        self.retry(exc=e, countdown=60)
