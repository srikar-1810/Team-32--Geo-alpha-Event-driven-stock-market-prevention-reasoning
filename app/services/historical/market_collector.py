from __future__ import annotations

import asyncio
import statistics
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.logging_config import get_logger
from app.models.market_data import MarketDataPoint
from app.services.historical.models import (
    AffectedStock,
    ImpactDirection,
    SectorImpact,
)
from app.services.tiingo.client import TiingoClient, SECTOR_ETF_MAP
from app.services.yahoo.client import YahooFinanceClient

logger = get_logger(__name__)

SECTOR_TICKER_MAP: Dict[str, List[str]] = {
    "XLF": ["JPM", "BAC", "C", "WFC", "GS", "MS", "BLK", "AXP", "V", "MA"],
    "XLE": ["XOM", "CVX", "COP", "EOG", "SLB", "OXY", "PXD", "HAL", "MPC", "VLO"],
    "XLK": ["AAPL", "MSFT", "NVDA", "AVGO", "CSCO", "ADBE", "CRM", "INTC", "AMD", "QCOM"],
    "XLV": ["UNH", "JNJ", "PFE", "ABBV", "MRK", "TMO", "ABT", "DHR", "BMY", "LLY"],
    "XLI": ["CAT", "GE", "HON", "MMM", "UNP", "BA", "LMT", "RTX", "UPS", "FDX"],
    "XLB": ["LIN", "APD", "ECL", "SHW", "DOW", "NEM", "FCX", "PPG", "DD", "ALB"],
    "XLU": ["NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "PEG", "ED"],
    "XLY": ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "LOW", "TJX", "GM", "F"],
    "XLP": ["PG", "KO", "PEP", "WMT", "COST", "PM", "MO", "CL", "KMB", "GIS"],
    "XLRE": ["PLD", "AMT", "EQIX", "CCI", "SPG", "WELL", "PSA", "DLR", "O", "AVB"],
    "XLC": ["META", "GOOGL", "GOOG", "NFLX", "DIS", "CMCSA", "CHTR", "T", "VZ", "TMUS"],
}


class HistoricalMarketCollector:
    """Collects historical market data around geopolitical events."""

    def __init__(
        self,
        tiingo: Optional[TiingoClient] = None,
        yahoo: Optional[YahooFinanceClient] = None,
    ) -> None:
        self.tiingo = tiingo or TiingoClient()
        self.yahoo = yahoo or YahooFinanceClient()

    async def collect_sector_data(
        self,
        event_date: date,
        window_days_before: int = 10,
        window_days_after: int = 30,
        sector_etfs: Optional[List[str]] = None,
    ) -> List[SectorImpact]:
        """Collect sector ETF data around an event date."""
        targets = sector_etfs or list(SECTOR_ETF_MAP.keys())[:15]
        start = event_date - timedelta(days=window_days_before + 5)
        end = event_date + timedelta(days=window_days_after + 5)

        all_prices = await self.tiingo.get_sector_etf_prices(
            start_date=start,
            end_date=end,
        )

        event_ts = datetime.combine(event_date, datetime.min.time()).replace(tzinfo=timezone.utc)

        sector_impacts: List[SectorImpact] = []
        for ticker in targets:
            points = all_prices.get(ticker, [])
            if len(points) < 5:
                try:
                    yahoo_prices = await self.yahoo.get_market_data_points(ticker, start, end)
                    points = [
                        MarketDataPoint(
                            ticker=p.ticker, date=p.date, open_price=p.open_price,
                            high_price=p.high_price, low_price=p.low_price,
                            close_price=p.close_price, volume=p.volume,
                            adj_close=p.adj_close, change_pct=p.change_pct,
                            source="yahoo",
                        )
                        for p in yahoo_prices
                    ]
                except Exception:
                    points = []

            if len(points) < 5:
                continue

            sector_name = SECTOR_ETF_MAP.get(ticker, ticker)
            impact = self._compute_sector_impact(ticker, sector_name, points, event_date)
            if impact:
                sector_impacts.append(impact)

        return sector_impacts

    async def collect_stock_data(
        self,
        tickers: List[str],
        event_date: date,
        window_before: int = 10,
        window_after: int = 30,
    ) -> List[AffectedStock]:
        """Collect individual stock data around an event date."""
        start = event_date - timedelta(days=window_before + 5)
        end = event_date + timedelta(days=window_after + 5)

        stocks: List[AffectedStock] = []
        for ticker in tickers:
            try:
                raw = await self.tiingo.get_daily_prices(ticker, start, end)
                points = [
                    await self.tiingo.to_market_model(r, ticker) for r in raw
                ]
            except Exception:
                try:
                    yahoo_pts = await self.yahoo.get_market_data_points(ticker, start, end)
                    points = yahoo_pts
                except Exception:
                    points = []

            if len(points) < 5:
                continue

            stock = self._compute_stock_impact(ticker, points, event_date)
            if stock:
                stocks.append(stock)

        return stocks

    def _compute_sector_impact(
        self,
        ticker: str,
        sector_name: str,
        points: List[MarketDataPoint],
        event_date: date,
    ) -> Optional[SectorImpact]:
        sorted_pts = sorted(points, key=lambda p: p.date)
        event_idx = None
        for i, p in enumerate(sorted_pts):
            if p.date >= event_date:
                event_idx = i
                break

        if event_idx is None or event_idx < 2:
            return None

        before = sorted_pts[:event_idx]
        after = sorted_pts[event_idx:]

        pre_close = before[-1].close_price if before else 0.0
        post_1d = after[1].close_price if len(after) > 1 else pre_close
        post_5d = after[5].close_price if len(after) > 5 else pre_close
        post_10d = after[10].close_price if len(after) > 10 else pre_close
        post_30d = after[min(30, len(after) - 1)].close_price if len(after) > min(30, len(after)) else pre_close

        r1d = ((post_1d - pre_close) / pre_close) * 100 if pre_close > 0 else 0.0
        r5d = ((post_5d - pre_close) / pre_close) * 100 if pre_close > 0 else 0.0
        r10d = ((post_10d - pre_close) / pre_close) * 100 if pre_close > 0 else 0.0
        r30d = ((post_30d - pre_close) / pre_close) * 100 if pre_close > 0 else 0.0

        before_returns = []
        for i in range(1, len(before)):
            if before[i - 1].close_price > 0:
                before_returns.append((before[i].close_price - before[i - 1].close_price) / before[i - 1].close_price)

        after_returns = []
        for i in range(1, len(after)):
            if after[i - 1].close_price > 0:
                after_returns.append((after[i].close_price - after[i - 1].close_price) / after[i - 1].close_price)

        vol_before = statistics.stdev(before_returns) if len(before_returns) > 2 else 0.0
        vol_after = statistics.stdev(after_returns) if len(after_returns) > 2 else 0.0

        impact_score = abs(r5d) / 10.0 if abs(r5d) > 0 else 0.0
        impact_score = min(1.0, impact_score)

        if r5d > 2.0:
            direction = ImpactDirection.BULLISH
        elif r5d < -2.0:
            direction = ImpactDirection.BEARISH
        else:
            direction = ImpactDirection.NEUTRAL

        vol_impact = ((vol_after - vol_before) / vol_before) * 100 if vol_before > 0 else 0.0

        return SectorImpact(
            sector_name=sector_name,
            etf_ticker=ticker,
            impact_score=round(impact_score, 4),
            direction=direction,
            return_1d=round(r1d, 2),
            return_5d=round(r5d, 2),
            return_10d=round(r10d, 2),
            return_30d=round(r30d, 2),
            volatility_impact=round(vol_impact, 2),
            stocks=[],
        )

    def _compute_stock_impact(
        self,
        ticker: str,
        points: List[Any],
        event_date: date,
    ) -> Optional[AffectedStock]:
        sorted_pts = sorted(points, key=lambda p: p.date if hasattr(p, 'date') else p.get('date', event_date))
        event_idx = None
        for i, p in enumerate(sorted_pts):
            pd = p.date if hasattr(p, 'date') else p.get('date', event_date)
            if pd >= event_date:
                event_idx = i
                break

        if event_idx is None or event_idx < 2:
            return None

        def get_close(p):
            if hasattr(p, 'close_price'):
                return p.close_price
            return p.get('close_price', p.get('close', 0.0))

        before = sorted_pts[:event_idx]
        after = sorted_pts[event_idx:]
        pre = get_close(before[-1]) if before else 0.0

        post_1d = get_close(after[1]) if len(after) > 1 else pre
        post_5d = get_close(after[5]) if len(after) > 5 else pre
        post_10d = get_close(after[10]) if len(after) > 10 else pre
        post_30d = get_close(after[min(30, len(after) - 1)]) if len(after) > min(30, len(after) - 1) else pre

        r1d = ((post_1d - pre) / pre) * 100 if pre > 0 else 0.0
        r5d = ((post_5d - pre) / pre) * 100 if pre > 0 else 0.0
        r10d = ((post_10d - pre) / pre) * 100 if pre > 0 else 0.0
        r30d = ((post_30d - pre) / pre) * 100 if pre > 0 else 0.0

        before_volumes = [p.volume if hasattr(p, 'volume') else p.get('volume', 0) for p in before[-5:]]
        after_volumes = [p.volume if hasattr(p, 'volume') else p.get('volume', 0) for p in after[:5]]
        avg_vol_before = sum(before_volumes) / len(before_volumes) if before_volumes else 1
        avg_vol_after = sum(after_volumes) / len(after_volumes) if after_volumes else 1
        vol_change = ((avg_vol_after - avg_vol_before) / avg_vol_before) * 100 if avg_vol_before > 0 else 0

        impact = abs(r5d) / 15.0
        impact = min(1.0, impact)

        if r5d > 3.0:
            direction = ImpactDirection.BULLISH
        elif r5d < -3.0:
            direction = ImpactDirection.BEARISH
        else:
            direction = ImpactDirection.NEUTRAL

        confidence = min(1.0, len(after) / 10.0)

        return AffectedStock(
            ticker=ticker,
            pre_event_price=round(pre, 2),
            post_event_price=round(post_5d, 2),
            return_1d=round(r1d, 2),
            return_5d=round(r5d, 2),
            return_10d=round(r10d, 2),
            return_30d=round(r30d, 2),
            volume_change_pct=round(vol_change, 2),
            impact_score=round(impact, 4),
            direction=direction,
            confidence=round(confidence, 4),
        )

    async def close(self) -> None:
        await self.tiingo.close()
        await self.yahoo.close()
