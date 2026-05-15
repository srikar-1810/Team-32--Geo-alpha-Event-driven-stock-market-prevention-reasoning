from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.config import settings
from app.logging_config import get_logger
from app.models.market_data import MarketDataPoint
from app.services.base import BaseService, default_retry
from app.services.yahoo.models import (
    YahooHistoricalPrice,
    YahooMarketSummary,
    YahooQuote,
    YahooSectorPerformance,
)

logger = get_logger(__name__)

YAHOO_CRUMB_URL = "https://fc.yahoo.com/ws/DownloadCrumb/v1"
YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
YAHOO_SPARK_URL = "https://query1.finance.yahoo.com/v7/finance/spark"

SECTOR_ETF_MAP: Dict[str, str] = {
    "XLF": "Financial",
    "XLE": "Energy",
    "XLK": "Technology",
    "XLV": "Health Care",
    "XLI": "Industrial",
    "XLB": "Materials",
    "XLRE": "Real Estate",
    "XLU": "Utilities",
    "XLY": "Consumer Cyclical",
    "XLP": "Consumer Defensive",
    "XLC": "Communication",
    "SPY": "S&P 500",
    "QQQ": "NASDAQ",
    "IWM": "Small Cap",
    "EEM": "Emerging Markets",
    "EFA": "Developed Markets",
    "VNQ": "Real Estate",
    "GLD": "Gold",
    "SLV": "Silver",
    "USO": "Oil",
    "TLT": "Long Term Treasuries",
    "SHY": "Short Term Treasuries",
    "AGG": "Aggregate Bonds",
    "LQD": "Corporate Bonds",
    "HYG": "High Yield Bonds",
    "VIX": "Volatility Index",
}

CORE_TICKERS: List[str] = list(SECTOR_ETF_MAP.keys())


class YahooFinanceClient(BaseService):
    """Fallback async client for Yahoo Finance market data (when Tiingo is unavailable)."""

    def __init__(self) -> None:
        super().__init__("yahoo_finance")
        self._client: Optional[httpx.AsyncClient] = None
        self._crumb: Optional[str] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                                  "Chrome/120.0.0.0 Safari/537.36",
                },
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=30),
            )
        return self._client

    @default_retry(max_attempts=3)
    async def get_quotes(self, tickers: List[str]) -> Dict[str, YahooQuote]:
        """Fetch current quote data for a list of tickers."""
        if not tickers:
            return {}
        client = await self._get_client()
        symbols = ",".join(tickers)
        response = await client.get(
            YAHOO_QUOTE_URL,
            params={"symbols": symbols, "fields": "symbol,regularMarketPrice,regularMarketChange,"
                                                  "regularMarketChangePercent,regularMarketVolume,"
                                                  "averageDailyVolume10Day,marketCap,trailingPE,"
                                                  "dividendYield,fiftyTwoWeekHigh,fiftyTwoWeekLow,beta,"
                                                  "shortName,longName"},
        )
        response.raise_for_status()
        data = response.json()
        results = {}

        for item in data.get("quoteResponse", {}).get("result", []):
            ticker = item.get("symbol", "")
            results[ticker] = YahooQuote(
                ticker=ticker,
                name=item.get("shortName") or item.get("longName", ""),
                price=item.get("regularMarketPrice", 0.0) or 0.0,
                change=item.get("regularMarketChange", 0.0) or 0.0,
                change_pct=item.get("regularMarketChangePercent", 0.0) or 0.0,
                volume=item.get("regularMarketVolume", 0) or 0,
                avg_volume=item.get("averageDailyVolume10Day", 0) or 0,
                market_cap=item.get("marketCap", 0.0) or 0.0,
                pe_ratio=item.get("trailingPE"),
                dividend_yield=item.get("dividendYield"),
                fifty_two_week_high=item.get("fiftyTwoWeekHigh"),
                fifty_two_week_low=item.get("fiftyTwoWeekLow"),
                beta=item.get("beta"),
                timestamp=datetime.now(timezone.utc),
            )

        return results

    @default_retry(max_attempts=3)
    async def get_historical_prices(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        interval: str = "1d",
    ) -> List[YahooHistoricalPrice]:
        """Fetch historical price data for a ticker."""
        client = await self._get_client()
        period1 = int(datetime.combine(start_date, datetime.min.time()).timestamp())
        period2 = int(datetime.combine(end_date, datetime.min.time()).timestamp())

        response = await client.get(
            f"{YAHOO_CHART_URL}/{ticker}",
            params={
                "period1": period1,
                "period2": period2,
                "interval": interval,
                "includePrePost": "false",
            },
        )
        response.raise_for_status()
        data = response.json()

        result = data.get("chart", {}).get("result", [{}])[0]
        timestamps = result.get("timestamp", [])
        quotes = result.get("indicators", {}).get("quote", [{}])[0]
        adjclose_data = result.get("indicators", {}).get("adjclose", [{}])[0]

        prices: List[YahooHistoricalPrice] = []
        for i, ts in enumerate(timestamps):
            dt = datetime.fromtimestamp(ts, tz=timezone.utc).date()
            opens = quotes.get("open", [])
            highs = quotes.get("high", [])
            lows = quotes.get("low", [])
            closes = quotes.get("close", [])
            volumes = quotes.get("volume", [])
            adj_closes = adjclose_data.get("adjclose", [])

            if i < len(opens) and opens[i] is not None:
                prices.append(YahooHistoricalPrice(
                    date=dt,
                    open=opens[i],
                    high=highs[i] if i < len(highs) and highs[i] else opens[i],
                    low=lows[i] if i < len(lows) and lows[i] else opens[i],
                    close=closes[i] if i < len(closes) and closes[i] else opens[i],
                    volume=volumes[i] if i < len(volumes) and volumes[i] else 0,
                    adj_close=adj_closes[i] if i < len(adj_closes) and adj_closes[i] else closes[i],
                ))

        return prices

    async def get_sector_performance(self) -> List[YahooSectorPerformance]:
        """Fetch current performance for all sector ETFs."""
        quotes = await self.get_quotes(CORE_TICKERS)
        performances = []
        for ticker, etf_sector in SECTOR_ETF_MAP.items():
            quote = quotes.get(ticker)
            if quote:
                performances.append(YahooSectorPerformance(
                    sector=etf_sector,
                    etf_ticker=ticker,
                    change_pct=quote.change_pct,
                    price=quote.price,
                    volume=quote.volume,
                ))
        return performances

    async def get_market_summary(self) -> YahooMarketSummary:
        """Fetch a comprehensive market summary including gainers, losers, sectors, VIX."""
        quotes = await self.get_quotes(CORE_TICKERS)

        gainers: List[YahooQuote] = []
        losers: List[YahooQuote] = []
        most_active: List[YahooQuote] = []
        sector_perf: List[YahooSectorPerformance] = []

        for ticker, etf_sector in SECTOR_ETF_MAP.items():
            quote = quotes.get(ticker)
            if not quote:
                continue
            if ticker == "VIX":
                continue

            sector_perf.append(YahooSectorPerformance(
                sector=etf_sector,
                etf_ticker=ticker,
                change_pct=quote.change_pct,
                price=quote.price,
                volume=quote.volume,
            ))

            if quote.change_pct > 0:
                gainers.append(quote)
            elif quote.change_pct < 0:
                losers.append(quote)
            most_active.append(quote)

        gainers.sort(key=lambda q: q.change_pct, reverse=True)
        losers.sort(key=lambda q: q.change_pct)
        most_active.sort(key=lambda q: q.volume, reverse=True)

        vix_quote = quotes.get("VIX")
        vix_level = vix_quote.price if vix_quote else 15.0

        return YahooMarketSummary(
            top_gainers=gainers[:10],
            top_losers=losers[:10],
            most_active=most_active[:10],
            sector_performance=sector_perf,
            vix_level=vix_level,
            timestamp=datetime.now(timezone.utc),
        )

    async def get_market_data_points(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> List[MarketDataPoint]:
        """Fetch historical prices and convert to MarketDataPoint models."""
        yahoo_prices = await self.get_historical_prices(ticker, start_date, end_date)
        points = []
        for yp in yahoo_prices:
            points.append(MarketDataPoint(
                ticker=ticker,
                date=yp.date,
                open_price=yp.open,
                high_price=yp.high,
                low_price=yp.low,
                close_price=yp.close,
                volume=yp.volume,
                adj_close=yp.adj_close,
                change_pct=0.0,
                source="yahoo",
            ))

        for i in range(1, len(points)):
            prev_close = points[i - 1].close_price
            if prev_close > 0:
                points[i].change_pct = round(
                    ((points[i].close_price - prev_close) / prev_close) * 100, 4
                )

        return points

    async def compute_technical_indicators(
        self,
        ticker: str,
        days: int = 100,
    ) -> Dict[str, Any]:
        """Compute volatility, momentum, and technical indicators from historical data."""
        end = date.today()
        start = end - timedelta(days=days)
        points = await self.get_market_data_points(ticker, start, end)

        if len(points) < 10:
            return {"ticker": ticker, "error": "insufficient data"}

        closes = [p.close_price for p in points]

        daily_returns = []
        for i in range(1, len(closes)):
            if closes[i - 1] > 0:
                daily_returns.append((closes[i] - closes[i - 1]) / closes[i - 1])

        import statistics
        realized_vol = statistics.stdev(daily_returns) * (252 ** 0.5) if len(daily_returns) > 1 else 0.0

        sma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
        sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else None

        rsi = self._compute_rsi(closes, 14)

        momentum_10d = ((closes[-1] - closes[-10]) / closes[-10]) * 100 if len(closes) >= 10 else 0.0
        momentum_20d = ((closes[-1] - closes[-20]) / closes[-20]) * 100 if len(closes) >= 20 else 0.0

        twenty_day_high = max(closes[-20:]) if len(closes) >= 20 else closes[-1]
        twenty_day_low = min(closes[-20:]) if len(closes) >= 20 else closes[-1]

        return {
            "ticker": ticker,
            "current_price": closes[-1] if closes else 0.0,
            "realized_volatility_annualized": round(realized_vol, 6),
            "daily_volatility": round(statistics.stdev(daily_returns), 6) if daily_returns else 0.0,
            "rsi_14": round(rsi, 2),
            "sma_20": round(sma_20, 2) if sma_20 else None,
            "sma_50": round(sma_50, 2) if sma_50 else None,
            "momentum_10d_pct": round(momentum_10d, 2),
            "momentum_20d_pct": round(momentum_20d, 2),
            "twenty_day_high": round(twenty_day_high, 2),
            "twenty_day_low": round(twenty_day_low, 2),
            "distance_from_20d_high_pct": round(
                ((closes[-1] - twenty_day_high) / twenty_day_high) * 100, 2
            ),
            "distance_from_20d_low_pct": round(
                ((closes[-1] - twenty_day_low) / twenty_day_low) * 100, 2
            ),
            "data_points": len(points),
            "is_overbought": rsi > 70,
            "is_oversold": rsi < 30,
            "trend": self._determine_trend(closes),
        }

    def _compute_rsi(self, closes: List[float], period: int = 14) -> float:
        if len(closes) < period + 1:
            return 50.0
        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0.0 for d in deltas]
        losses = [-d if d < 0 else 0.0 for d in deltas]

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return round(100.0 - (100.0 / (1.0 + rs)), 2)

    def _determine_trend(self, closes: List[float]) -> str:
        if len(closes) < 20:
            return "neutral"
        sma_short = sum(closes[-5:]) / 5
        sma_long = sum(closes[-20:]) / 20
        recent = closes[-5:]
        trend_up = all(recent[i] >= recent[i - 1] for i in range(1, len(recent)))
        trend_down = all(recent[i] <= recent[i - 1] for i in range(1, len(recent)))

        if sma_short > sma_long and trend_up:
            return "strong_uptrend"
        if sma_short > sma_long:
            return "uptrend"
        if sma_short < sma_long and trend_down:
            return "strong_downtrend"
        if sma_short < sma_long:
            return "downtrend"
        return "neutral"

    @property
    def is_available(self) -> bool:
        return True

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self) -> YahooFinanceClient:
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()
