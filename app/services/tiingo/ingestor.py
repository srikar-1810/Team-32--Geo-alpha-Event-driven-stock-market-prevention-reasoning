from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from app.config import settings
from app.logging_config import get_logger
from app.models.market_data import MarketDataPoint
from app.services.base import default_retry
from app.services.tiingo.client import TiingoClient, SECTOR_ETF_TICKERS, SECTOR_ETF_MAP
from app.utils.rate_limiter import RateLimiter

logger = get_logger(__name__)

MARKET_HOURS_START = 9 * 60 + 30
MARKET_HOURS_END = 16 * 60


def _is_market_open() -> bool:
    now = datetime.now(timezone.utc)
    est = now - timedelta(hours=5)
    if est.weekday() >= 5:
        return False
    minutes_since_midnight = est.hour * 60 + est.minute
    return MARKET_HOURS_START <= minutes_since_midnight <= MARKET_HOURS_END


class MarketDataIngestor:
    """Scheduled market data ingestor with sector ETF tracking, volatility, momentum, and Yahoo fallback."""

    def __init__(self, client: Optional[TiingoClient] = None) -> None:
        self.client = client or TiingoClient()
        self._last_run: Optional[datetime] = None
        self._run_count: int = 0
        self._total_ingested: int = 0
        self._errors: int = 0
        self._rate_limiter = RateLimiter(
            max_calls=60,
            period=60.0,
            name="market_ingestor",
        )

    @default_retry(max_attempts=3)
    async def ingest_sector_etfs(
        self,
        days_back: int = 30,
    ) -> Dict[str, Any]:
        """Fetch daily prices for all sector ETFs and compute performance."""
        end = date.today()
        start = end - timedelta(days=days_back)

        logger.info("Market ingestion: %d sector ETFs, %d days", len(SECTOR_ETF_TICKERS), days_back)

        async with self._rate_limiter:
            try:
                sector_data = await self.client.get_sector_etf_prices(start, end)
            except Exception as e:
                self._errors += 1
                logger.error("Sector ETF fetch failed: %s", e)
                return {"status": "error", "error": str(e)}

        sector_performance: Dict[str, Dict[str, Any]] = {}
        total_points = 0

        for ticker, points in sector_data.items():
            total_points += len(points)
            sector_name = SECTOR_ETF_MAP.get(ticker, ticker)
            perf = self._compute_etf_performance(ticker, points)
            sector_performance[ticker] = {
                "sector": sector_name,
                **perf,
            }

        market_health = await self.client.get_market_health()

        self._total_ingested += total_points
        self._run_count += 1
        self._last_run = datetime.now(timezone.utc)

        logger.info(
            "Market ingestion: %d ETFs, %d data points, %d sectors positive",
            len(sector_data), total_points,
            market_health.get("advancing_sectors", 0),
        )

        return {
            "status": "success",
            "source": "tiingo",
            "run_count": self._run_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sectors_fetched": len(sector_data),
            "total_data_points": total_points,
            "total_ingested_cumulative": self._total_ingested,
            "sector_performance": sector_performance,
            "market_health": market_health,
            "days_back": days_back,
        }

    @default_retry(max_attempts=2)
    async def ingest_realtime_prices(
        self,
        tickers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Fetch real-time IEX prices for key tickers (during market hours)."""
        target = tickers or SECTOR_ETF_TICKERS[:15]
        logger.info("Market real-time ingestion: %d tickers", len(target))

        async with self._rate_limiter:
            try:
                iex_data = await self.client.get_iex_data(target)
            except Exception as e:
                self._errors += 1
                logger.error("Real-time prices failed: %s", e)
                return {"status": "error", "error": str(e)}

        quotes = {}
        for item in iex_data:
            ticker = item.get("ticker", "")
            if ticker:
                last = item.get("lastSalePrice", item.get("tngoLast", 0)) or 0
                prev = item.get("prevClose", 0) or 0
                change_pct = ((last - prev) / prev * 100) if prev > 0 else 0
                quotes[ticker] = {
                    "ticker": ticker,
                    "last_price": round(last, 2),
                    "change_pct": round(change_pct, 2),
                    "volume": item.get("volume", 0),
                    "bid": item.get("bidPrice"),
                    "ask": item.get("askPrice"),
                    "timestamp": item.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    "market_open": _is_market_open(),
                }

        self._run_count += 1
        self._last_run = datetime.now(timezone.utc)

        return {
            "status": "success",
            "source": "tiingo_iex",
            "run_count": self._run_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tickers_fetched": len(quotes),
            "quotes": quotes,
            "market_open": _is_market_open(),
        }

    async def ingest_volatility_momentum(
        self,
        tickers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Compute volatility and momentum indicators for key tickers."""
        target = tickers or ["SPY", "QQQ", "IWM", "EEM", "XLF", "XLE", "XLK"]

        logger.info("Market vol/mom ingestion: %d tickers", len(target))
        results: Dict[str, Any] = {}

        for ticker in target:
            try:
                vol = await self.client.compute_volatility(ticker, days=20)
                mom = await self.client.compute_momentum(ticker)
                results[ticker] = {"volatility": vol, "momentum": mom}
            except Exception as e:
                logger.warning("Vol/mom failed for %s: %s", ticker, e)
                results[ticker] = {"error": str(e)}

        self._run_count += 1
        self._last_run = datetime.now(timezone.utc)

        return {
            "status": "success",
            "source": "tiingo_volatility",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tickers": target,
            "results": results,
        }

    def _compute_etf_performance(
        self,
        ticker: str,
        points: List[MarketDataPoint],
    ) -> Dict[str, Any]:
        if len(points) < 2:
            return {"error": "insufficient data", "data_points": len(points)}

        closes = [p.close_price for p in points]
        first_close = closes[0]
        last_close = closes[-1]
        period_return = ((last_close - first_close) / first_close) * 100 if first_close > 0 else 0.0

        daily_returns = []
        for i in range(1, len(closes)):
            if closes[i - 1] > 0:
                daily_returns.append((closes[i] - closes[i - 1]) / closes[i - 1])

        import statistics
        vol = statistics.stdev(daily_returns) * (252 ** 0.5) if len(daily_returns) > 1 else 0.0

        sma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None

        high = max(closes)
        low = min(closes)
        high_date = points[closes.index(high)].date.isoformat() if closes.index(high) < len(points) else ""
        low_date = points[closes.index(low)].date.isoformat() if closes.index(low) < len(points) else ""

        return {
            "first_date": points[0].date.isoformat(),
            "last_date": points[-1].date.isoformat(),
            "first_close": round(first_close, 2),
            "last_close": round(last_close, 2),
            "period_return_pct": round(period_return, 2),
            "annualized_volatility": round(vol, 6),
            "sma_20": round(sma_20, 2) if sma_20 else None,
            "period_high": round(high, 2),
            "period_high_date": high_date,
            "period_low": round(low, 2),
            "period_low_date": low_date,
            "data_points": len(points),
        }

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "source": "tiingo",
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "run_count": self._run_count,
            "total_ingested": self._total_ingested,
            "errors": self._errors,
        }

    async def close(self) -> None:
        await self.client.close()
