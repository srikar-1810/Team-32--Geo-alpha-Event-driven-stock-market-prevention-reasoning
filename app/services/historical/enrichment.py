from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.logging_config import get_logger
from app.services.historical.models import HistoricalMarketImpact

logger = get_logger(__name__)

MACRO_MARKERS: Dict[str, Dict[str, Any]] = {
    "SPY": {
        "asset_type": "equity_index",
        "label": "S&P 500",
        "description": "US large-cap stock market index",
    },
    "QQQ": {
        "asset_type": "equity_index",
        "label": "Nasdaq 100",
        "description": "US technology-heavy stock index",
    },
    "IWM": {
        "asset_type": "equity_index",
        "label": "Russell 2000",
        "description": "US small-cap stock index",
    },
    "EEM": {
        "asset_type": "equity_index",
        "label": "Emerging Markets",
        "description": "MSCI emerging markets index",
    },
    "TLT": {
        "asset_type": "bond",
        "label": "20+ Year Treasury",
        "description": "US long-term government bonds",
    },
    "SHY": {
        "asset_type": "bond",
        "label": "1-3 Year Treasury",
        "description": "US short-term government bonds",
    },
    "HYG": {
        "asset_type": "bond",
        "label": "High Yield Corporate",
        "description": "US high-yield corporate bonds",
    },
    "GLD": {
        "asset_type": "commodity",
        "label": "Gold",
        "description": "Gold spot price ETF",
    },
    "USO": {
        "asset_type": "commodity",
        "label": "Crude Oil",
        "description": "US crude oil fund",
    },
    "DXY": {
        "asset_type": "currency",
        "label": "US Dollar Index",
        "description": "USD strength vs major currencies",
    },
}


class EventEnricher:
    """Enriches historical events with macroeconomic context and metadata."""

    def __init__(self) -> None:
        self._sector_map_cache: Dict[str, Dict[str, Any]] = {}

    async def enrich_event(
        self,
        event: HistoricalMarketImpact,
        macro_data: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> HistoricalMarketImpact:
        """Apply all enrichment pipelines to a single event."""
        event = self._enrich_with_macro_context(event, macro_data)
        event = self._enrich_with_historical_analogues(event)
        return event

    def _enrich_with_macro_context(
        self,
        event: HistoricalMarketImpact,
        macro_data: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> HistoricalMarketImpact:
        if not macro_data:
            return event

        macro_lines: List[str] = []
        for ticker, data in macro_data.items():
            info = MACRO_MARKERS.get(ticker, {})
            label = info.get("label", ticker)
            asset_type = info.get("asset_type", "unknown")

            ret_5d = data.get("return_5d", 0.0)
            ret_30d = data.get("return_30d", 0.0)
            vol_change = data.get("volatility_change", 0.0)

            macro_lines.append(
                f"  {label} ({asset_type}): 5d={ret_5d:+.2f}% 30d={ret_30d:+.2f}% vol={vol_change:+.2f}%"
            )

            if ticker == "DXY":
                dxy_5d = data.get("return_5d", 0.0)
                if dxy_5d > 2.0:
                    logger.debug("USD strengthening detected (DXY +%.2f%%)", dxy_5d)
                elif dxy_5d < -2.0:
                    logger.debug("USD weakening detected (DXY %.2f%%)", dxy_5d)

        macro_context = "Macro context:\n" + "\n".join(macro_lines) if macro_lines else ""

        existing = event.impact_summary or ""
        if macro_context:
            parts = [existing, macro_context] if existing else [macro_context]
            event.impact_summary = "\n\n".join(parts)

        return event

    def _enrich_with_historical_analogues(
        self,
        event: HistoricalMarketImpact,
    ) -> HistoricalMarketImpact:
        analogues: List[str] = []

        base_categories: Dict[str, List[str]] = {
            "war": ["WWII", "Gulf War", "Iraq War", "Ukraine War", "Israel-Hamas War", "Six-Day War", "Falklands War"],
            "sanctions": ["Iran Sanctions 2012", "Russia Sanctions 2014", "Russia Sanctions 2022"],
            "election": ["US Election 2008", "US Election 2016", "US Election 2020", "Brexit 2016"],
            "crisis": ["2008 Financial Crisis", "Asian Financial Crisis 1997", "Debt Ceiling 2011", "COVID-19 2020"],
            "terrorism": ["9/11", "Paris Attacks 2015", "Boston Bombing 2013"],
            "oil": ["Oil Price Crash 2014", "Oil Price War 2020", "1973 Oil Crisis"],
            "natural disaster": ["Hurricane Katrina 2005", "Fukushima 2011", "Japan Earthquake 2011"],
            "trade": ["US-China Trade War 2018", "NAFTA Renegotiation 2018"],
            "pandemic": ["COVID-19 2020", "SARS 2003", "H1N1 2009", "Ebola 2014"],
            "cyberattack": ["NotPetya 2017", "SolarWinds 2020", "Colonial Pipeline 2021"],
        }

        event_type_lower = event.event_type.lower()
        for category, examples in base_categories.items():
            if category in event_type_lower:
                analogues.extend(examples)

        if not analogues:
            for sector in event.sectors_impacted:
                if sector.return_5d < -10:
                    analogues.append(f"Historical {sector.sector_name} selloff (similar magnitude)")
                    break

        event.historical_analogues = analogues
        return event

    def _calculate_volatility_metrics(
        self,
        event: HistoricalMarketImpact,
    ) -> HistoricalMarketImpact:
        if event.sectors_impacted:
            vol_changes = [s.volatility_impact for s in event.sectors_impacted]
            event.volatility_change_pct = (
                sum(vol_changes) / len(vol_changes) if vol_changes else 0.0
            )
        return event


class MacroCollector:
    """Collects macroeconomic context data around event dates."""

    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}

    async def collect_macro_context(
        self,
        event_date: date,
        window_days: int = 30,
    ) -> Dict[str, Dict[str, float]]:
        context: Dict[str, Dict[str, float]] = {}
        macro_tickers = list(MACRO_MARKERS.keys())

        for ticker in macro_tickers:
            try:
                data = await self._fetch_ticker_data(ticker, event_date, window_days)
                if data:
                    context[ticker] = data
            except Exception as e:
                logger.debug("Macro data fetch failed for %s: %s", ticker, e)

        return context

    async def _fetch_ticker_data(
        self,
        ticker: str,
        event_date: date,
        window_days: int,
    ) -> Optional[Dict[str, float]]:
        from app.services.yahoo.client import YahooFinanceClient

        client = YahooFinanceClient()
        try:
            start = event_date - timedelta(days=window_days + 10)
            end = event_date + timedelta(days=window_days + 10)

            points = await client.get_market_data_points(ticker, start, end)
            if len(points) < 5:
                return None

            sorted_pts = sorted(points, key=lambda p: p.date)
            event_idx = None
            for i, p in enumerate(sorted_pts):
                if p.date >= event_date:
                    event_idx = i
                    break

            if event_idx is None or event_idx < 2:
                return None

            pre = sorted_pts[event_idx - 1].close_price if event_idx > 0 else sorted_pts[0].close_price
            post_5 = sorted_pts[min(event_idx + 5, len(sorted_pts) - 1)].close_price if event_idx + 5 < len(sorted_pts) else pre
            post_30 = sorted_pts[min(event_idx + 30, len(sorted_pts) - 1)].close_price if event_idx + 30 < len(sorted_pts) else pre

            before_returns = []
            for i in range(max(1, event_idx - 20), event_idx):
                if sorted_pts[i].close_price > 0:
                    before_returns.append(
                        (sorted_pts[i].close_price - sorted_pts[i - 1].close_price) / sorted_pts[i - 1].close_price
                    )

            after_returns = []
            for i in range(event_idx + 1, min(event_idx + 21, len(sorted_pts))):
                if sorted_pts[i - 1].close_price > 0:
                    after_returns.append(
                        (sorted_pts[i].close_price - sorted_pts[i - 1].close_price) / sorted_pts[i - 1].close_price
                    )

            import statistics
            vol_before = statistics.stdev(before_returns) if len(before_returns) > 2 else 0.0
            vol_after = statistics.stdev(after_returns) if len(after_returns) > 2 else 0.0
            vol_change = ((vol_after - vol_before) / vol_before) * 100 if vol_before > 0 else 0.0

            return {
                "return_5d": round(((post_5 - pre) / pre) * 100, 2),
                "return_30d": round(((post_30 - pre) / pre) * 100, 2),
                "volatility_change": round(vol_change, 2),
            }
        finally:
            await client.close()
