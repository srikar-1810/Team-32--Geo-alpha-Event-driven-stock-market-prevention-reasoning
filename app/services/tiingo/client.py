from __future__ import annotations

import statistics
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.config import settings
from app.logging_config import get_logger
from app.models.market_data import MarketDataPoint
from app.services.base import BaseService, default_retry

logger = get_logger(__name__)

SECTOR_ETF_TICKERS: List[str] = [
    "SPY", "QQQ", "IWM", "EEM",
    "XLF", "XLE", "XLK", "XLV", "XLI", "XLB", "XLU", "XLY", "XLP", "XLRE", "XLC",
    "VNQ", "GLD", "SLV", "USO",
    "TLT", "SHY", "AGG", "LQD", "HYG",
    "VIX",
]

SECTOR_ETF_MAP: Dict[str, str] = {
    "SPY": "S&P 500", "QQQ": "NASDAQ-100", "IWM": "Russell 2000", "EEM": "Emerging Markets",
    "XLF": "Financials", "XLE": "Energy", "XLK": "Technology", "XLV": "Healthcare",
    "XLI": "Industrials", "XLB": "Materials", "XLU": "Utilities", "XLY": "Consumer Cyclical",
    "XLP": "Consumer Defensive", "XLRE": "Real Estate", "XLC": "Communication Services",
    "VNQ": "Real Estate", "GLD": "Gold", "SLV": "Silver", "USO": "Oil",
    "TLT": "Long-Term Treasury", "SHY": "Short-Term Treasury", "AGG": "Aggregate Bond",
    "LQD": "Corporate Bond", "HYG": "High-Yield Bond",
    "VIX": "Volatility Index",
}


class TiingoClient(BaseService):
    """Async client for Tiingo stock market data with sector ETF, volatility, and momentum analysis."""

    def __init__(self) -> None:
        super().__init__("tiingo")
        self.validate_config(["TIINGO_API_TOKEN", "TIINGO_BASE_URL"])
        self._client: Optional[httpx.AsyncClient] = None
        self._yahoo_fallback: Optional[YahooFinanceClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=settings.TIINGO_BASE_URL,
                timeout=settings.TIINGO_TIMEOUT,
                headers={
                    "Authorization": f"Token {settings.TIINGO_API_TOKEN}",
                    "Content-Type": "application/json",
                },
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=30),
            )
        return self._client

    @property
    def _yahoo(self):
        if self._yahoo_fallback is None:
            try:
                from app.services.yahoo.client import YahooFinanceClient as _YFC
                self._yahoo_fallback = _YFC()
            except ImportError:
                self._yahoo_fallback = None
        return self._yahoo_fallback

    @default_retry(max_attempts=settings.TIINGO_MAX_RETRIES)
    async def get_daily_prices(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        frequency: str = "daily",
    ) -> List[Dict[str, Any]]:
        client = await self._get_client()
        try:
            response = await client.get(
                f"/tiingo/daily/{ticker}/prices",
                params={
                    "startDate": start_date.isoformat(),
                    "endDate": end_date.isoformat(),
                    "resampleFreq": frequency,
                    "format": "json",
                },
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning("Tiingo daily prices failed for %s, trying Yahoo fallback: %s", ticker, e)
            if self._yahoo:
                yahoo_prices = await self._yahoo.get_market_data_points(ticker, start_date, end_date)
                return [
                    {
                        "date": p.date.isoformat(),
                        "open": p.open_price,
                        "high": p.high_price,
                        "low": p.low_price,
                        "close": p.close_price,
                        "volume": p.volume,
                        "adjClose": p.adj_close or p.close_price,
                    }
                    for p in yahoo_prices
                ]
            raise

    @default_retry(max_attempts=settings.TIINGO_MAX_RETRIES)
    async def get_ticker_metadata(self, ticker: str) -> Dict[str, Any]:
        client = await self._get_client()
        try:
            response = await client.get(f"/tiingo/daily/{ticker}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning("Tiingo metadata failed for %s: %s", ticker, e)
            return {"ticker": ticker, "name": ticker, "error": str(e)}

    @default_retry(max_attempts=settings.TIINGO_MAX_RETRIES)
    async def get_iex_data(
        self,
        tickers: List[str],
    ) -> List[Dict[str, Any]]:
        client = await self._get_client()
        try:
            response = await client.get(
                "/iex",
                params={"tickers": ",".join(tickers), "format": "json"},
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning("Tiingo IEX failed, trying Yahoo quotes: %s", e)
            if self._yahoo:
                quotes = await self._yahoo.get_quotes(tickers)
                return [
                    {
                        "ticker": ticker,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "lastSalePrice": q.price,
                        "lastSaleTimestamp": q.timestamp.isoformat(),
                        "tngoLast": q.price,
                        "prevClose": q.price - q.change,
                        "open": None,
                        "high": None,
                        "low": None,
                        "mid": None,
                        "volume": q.volume,
                        "bidPrice": None,
                        "askPrice": None,
                        "prevClosePct": q.change_pct,
                    }
                    for ticker, q in quotes.items()
                ]
            raise

    @default_retry(max_attempts=settings.TIINGO_MAX_RETRIES)
    async def get_news(
        self,
        tickers: List[str],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        client = await self._get_client()
        params: Dict[str, Any] = {
            "tickers": ",".join(tickers),
            "limit": min(limit, 100),
        }
        if start_date:
            params["startDate"] = start_date.isoformat()
        if end_date:
            params["endDate"] = end_date.isoformat()

        try:
            response = await client.get("/news", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning("Tiingo news failed: %s", e)
            return []

    async def get_sector_etf_prices(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        days_back: int = 30,
    ) -> Dict[str, List[MarketDataPoint]]:
        """Fetch daily prices for all sector ETFs."""
        end = end_date or date.today()
        start = start_date or (end - timedelta(days=days_back))

        results: Dict[str, List[MarketDataPoint]] = {}
        for ticker in SECTOR_ETF_TICKERS:
            try:
                raw = await self.get_daily_prices(ticker, start, end)
                points = []
                for r in raw:
                    point = await self.to_market_model(r, ticker)
                    points.append(point)
                results[ticker] = points
                logger.debug("Fetched %d days for %s", len(points), ticker)
            except Exception as e:
                logger.warning("Failed to fetch sector ETF %s: %s", ticker, e)

        return results

    async def compute_volatility(
        self,
        ticker: str,
        days: int = 20,
    ) -> Dict[str, Any]:
        """Compute realized volatility for a ticker."""
        end = date.today()
        start = end - timedelta(days=days + 10)
        try:
            raw = await self.get_daily_prices(ticker, start, end)
            points = [await self.to_market_model(r, ticker) for r in raw]
        except Exception:
            return {"ticker": ticker, "error": "failed to fetch data"}

        if len(points) < 5:
            return {"ticker": ticker, "error": "insufficient data"}

        closes = [p.close_price for p in points[-days:]]
        returns = []
        for i in range(1, len(closes)):
            if closes[i - 1] > 0:
                returns.append((closes[i] - closes[i - 1]) / closes[i - 1])

        if len(returns) < 2:
            return {"ticker": ticker, "volatility": 0.0}

        daily_vol = statistics.stdev(returns)
        annualized_vol = daily_vol * (252 ** 0.5)
        daily_mean = sum(returns) / len(returns)

        return {
            "ticker": ticker,
            "daily_volatility": round(daily_vol, 6),
            "annualized_volatility": round(annualized_vol, 6),
            "daily_mean_return": round(daily_mean, 6),
            "sharpe_ratio": round(daily_mean / daily_vol * (252 ** 0.5), 4) if daily_vol > 0 else 0.0,
            "sample_size": len(returns),
            "period_days": days,
        }

    async def compute_momentum(
        self,
        ticker: str,
        windows: List[int] = None,
    ) -> Dict[str, Any]:
        """Compute momentum indicators (returns over multiple windows)."""
        windows = windows or [5, 10, 20, 50, 100]
        max_window = max(windows) + 10
        end = date.today()
        start = end - timedelta(days=max_window)

        try:
            raw = await self.get_daily_prices(ticker, start, end)
            points = [await self.to_market_model(r, ticker) for r in raw]
        except Exception:
            return {"ticker": ticker, "error": "failed to fetch data"}

        if not points:
            return {"ticker": ticker, "error": "no data"}

        closes = [p.close_price for p in points]
        momentum = {}
        for window in windows:
            if len(closes) > window:
                prev = closes[-(window + 1)]
                curr = closes[-1]
                ret = ((curr - prev) / prev) * 100 if prev > 0 else 0.0
                momentum[f"momentum_{window}d_pct"] = round(ret, 2)

        rsi = self._compute_rsi(closes, 14)

        sma_windows = [20, 50, 200]
        smas = {}
        for w in sma_windows:
            if len(closes) >= w:
                smas[f"sma_{w}"] = round(sum(closes[-w:]) / w, 2)
            else:
                smas[f"sma_{w}"] = None

        return {
            "ticker": ticker,
            "current_price": closes[-1],
            **momentum,
            "rsi_14": round(rsi, 2),
            **smas,
            "data_points": len(closes),
        }

    async def get_market_health(self) -> Dict[str, Any]:
        """Compute overall market health from sector ETF performance."""
        end = date.today()
        start = end - timedelta(days=30)
        sector_data = await self.get_sector_etf_prices(start, end)

        sector_changes: Dict[str, float] = {}
        advancing = 0
        declining = 0
        total_vol = 0

        for ticker, points in sector_data.items():
            if len(points) >= 2:
                change = ((points[-1].close_price - points[0].close_price) / points[0].close_price) * 100
                sector_name = SECTOR_ETF_MAP.get(ticker, ticker)
                sector_changes[sector_name] = round(change, 2)
                if change > 0:
                    advancing += 1
                else:
                    declining += 1
                total_vol += points[-1].volume

        try:
            spy_vol = await self.compute_volatility("SPY", 20)
            spy_mom = await self.compute_momentum("SPY")
        except Exception:
            spy_vol = {}
            spy_mom = {}

        advance_decline_ratio = advancing / max(declining, 1)

        return {
            "sector_performance_30d": sector_changes,
            "advancing_sectors": advancing,
            "declining_sectors": declining,
            "advance_decline_ratio": round(advance_decline_ratio, 2),
            "total_volume": total_vol,
            "spy_volatility": spy_vol.get("annualized_volatility", 0),
            "spy_momentum": {
                "5d": spy_mom.get("momentum_5d_pct", 0),
                "20d": spy_mom.get("momentum_20d_pct", 0),
            },
            "spy_rsi": spy_mom.get("rsi_14", 50),
            "market_breadth": "strong" if advance_decline_ratio > 1.5 else
                              "weak" if advance_decline_ratio < 0.67 else "neutral",
        }

    @staticmethod
    def _compute_rsi(closes: List[float], period: int = 14) -> float:
        if len(closes) < period + 1:
            return 50.0
        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [max(d, 0.0) for d in deltas]
        losses = [max(-d, 0.0) for d in deltas]

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return round(100.0 - (100.0 / (1.0 + rs)), 2)

    async def to_market_model(self, raw: Dict[str, Any], ticker: str) -> MarketDataPoint:
        return MarketDataPoint(
            ticker=ticker,
            date=datetime.fromisoformat(raw.get("date", "")).date()
            if isinstance(raw.get("date"), str) and "T" in raw.get("date", "")
            else datetime.strptime(str(raw.get("date", ""))[:10], "%Y-%m-%d").date()
            if raw.get("date")
            else date.today(),
            open_price=float(raw.get("open", 0.0)),
            high_price=float(raw.get("high", 0.0)),
            low_price=float(raw.get("low", 0.0)),
            close_price=float(raw.get("close", 0.0)),
            volume=int(raw.get("volume", 0)),
            adj_close=float(raw.get("adjClose", raw.get("adj_close", 0))) or None,
            change_pct=float(raw.get("changePct", raw.get("change_pct", 0.0))) or None,
            source="tiingo",
            raw_data=raw,
        )

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        if self._yahoo_fallback:
            await self._yahoo_fallback.close()

    async def __aenter__(self) -> TiingoClient:
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()
