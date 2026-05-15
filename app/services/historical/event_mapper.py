from __future__ import annotations

from typing import Dict, List, Optional, Set

from app.logging_config import get_logger
from app.services.historical.market_collector import HistoricalMarketCollector, SECTOR_TICKER_MAP
from app.services.historical.models import (
    AffectedStock,
    HistoricalMarketImpact,
    ImpactDirection,
    SectorImpact,
)
from app.services.tiingo.client import SECTOR_ETF_MAP

logger = get_logger(__name__)

SECTOR_KEYWORD_MAP: Dict[str, List[str]] = {
    "XLF": ["bank", "financial", "lending", "interest rate", "fed", "federal reserve",
            "monetary policy", "banking", "finance", "credit", "mortgage", "insurance",
            "fintech", "blockchain", "crypto", "bitcoin"],
    "XLE": ["oil", "gas", "petroleum", "energy", "crude", "refinery", "drilling",
            "fracking", "opec", "natural gas", "coal", "renewable energy", "solar", "wind"],
    "XLK": ["technology", "software", "hardware", "semiconductor", "chip", "ai",
            "artificial intelligence", "cloud", "cyber", "data", "internet", "tech",
            "startup", "silicon valley", "encryption", "quantum"],
    "XLV": ["healthcare", "pharma", "pharmaceutical", "drug", "vaccine", "hospital",
            "biotech", "medical", "insurance", "medicare", "medicaid", "covid",
            "pandemic", "disease", "treatment", "surgery"],
    "XLI": ["manufacturing", "industrial", "defense", "aerospace", "military",
            "airline", "railway", "shipping", "logistics", "supply chain",
            "infrastructure", "construction", "engineering", "factory"],
    "XLB": ["chemical", "material", "mining", "steel", "aluminum", "copper",
            "lithium", "rare earth", "metals", "commodity", "fertilizer",
            "agriculture", "paper", "packaging"],
    "XLU": ["utility", "power", "electric", "grid", "nuclear", "renewable",
            "energy", "water", "gas utility", "infrastructure"],
    "XLY": ["consumer", "retail", "ecommerce", "amazon", "walmart", "restaurant",
            "automotive", "car", "travel", "tourism", "entertainment", "media",
            "luxury", "fashion", "sporting"],
    "XLP": ["consumer staple", "food", "beverage", "tobacco", "household",
            "personal care", "grocery", "supermarket", "cpg", "procter", "coca-cola"],
    "XLRE": ["real estate", "reit", "property", "housing", "commercial real estate",
             "office", "apartment", "rent", "mortgage", "construction"],
    "XLC": ["telecommunication", "telecom", "5g", "broadband", "cable",
            "streaming", "social media", "entertainment", "media", "content"],
    "GLD": ["gold", "precious metal", "safe haven", "inflation hedge", "central bank reserve"],
    "SLV": ["silver", "precious metal", "industrial metal"],
    "USO": ["oil", "crude", "petroleum", "gasoline", "energy commodity"],
    "TLT": ["bond", "treasury", "yield", "interest rate", "debt", "government bond"],
}

TOP_TICKERS: List[str] = []
for tickers in SECTOR_TICKER_MAP.values():
    TOP_TICKERS.extend(tickers[:5])


class EventMapper:
    """Maps geopolitical events to impacted sectors and stocks."""

    def __init__(
        self,
        market_collector: Optional[HistoricalMarketCollector] = None,
    ) -> None:
        self.market_collector = market_collector or HistoricalMarketCollector()

    def map_sectors_from_event(
        self,
        event: HistoricalMarketImpact,
        keywords: Optional[Dict[str, List[str]]] = None,
    ) -> List[str]:
        target = keywords or SECTOR_KEYWORD_MAP
        text = f"{event.event_title} {event.event_description} {event.event_type} {event.location}".lower()
        text += f" {' '.join(event.countries).lower()} {' '.join(event.actors).lower()}"

        matched: List[str] = []
        for sector, sector_kws in target.items():
            if any(kw.lower() in text for kw in sector_kws):
                matched.append(sector)

        return list(set(matched))

    async def enrich_with_market_data(
        self,
        event: HistoricalMarketImpact,
        sector_etfs: Optional[List[str]] = None,
    ) -> HistoricalMarketImpact:
        event_date = event.event_date.date()
        matched = sector_etfs or self.map_sectors_from_event(event)

        if not matched:
            matched = list(SECTOR_ETF_MAP.keys())[:3]

        sectors = await self.market_collector.collect_sector_data(
            event_date=event_date,
            sector_etfs=matched,
        )

        all_impacted_tickers: List[str] = []
        for sector_ticker in matched:
            stock_tickers = SECTOR_TICKER_MAP.get(sector_ticker, [])
            all_impacted_tickers.extend(stock_tickers[:5])

        stocks = await self.market_collector.collect_stock_data(
            tickers=all_impacted_tickers,
            event_date=event_date,
        )

        stock_map: Dict[str, AffectedStock] = {}
        for stock in stocks:
            stock_map[stock.ticker] = stock

        for sector in sectors:
            sector_stocks = []
            for ticker in SECTOR_TICKER_MAP.get(sector.etf_ticker, []):
                if ticker in stock_map:
                    sector_stocks.append(stock_map[ticker])
            sector.stocks = sector_stocks

        bullish_stocks = sorted(
            [s for s in stocks if s.direction == ImpactDirection.BULLISH and s.confidence > 0.3],
            key=lambda x: x.return_5d,
            reverse=True,
        )[:10]

        bearish_stocks = sorted(
            [s for s in stocks if s.direction == ImpactDirection.BEARISH and s.confidence > 0.3],
            key=lambda x: x.return_5d,
        )[:10]

        event.sectors_impacted = sectors
        event.top_bullish_stocks = [
            {"ticker": s.ticker, "return_5d": s.return_5d, "impact_score": s.impact_score}
            for s in bullish_stocks
        ]
        event.top_bearish_stocks = [
            {"ticker": s.ticker, "return_5d": s.return_5d, "impact_score": s.impact_score}
            for s in bearish_stocks
        ]
        event.impact_summary = self._generate_impact_summary(event)

        return event

    def _generate_impact_summary(self, event: HistoricalMarketImpact) -> str:
        bullish = event.top_bullish_stocks
        bearish = event.top_bearish_stocks
        sectors = event.sectors_impacted

        parts: List[str] = []
        parts.append(f"Event: {event.event_title}")
        parts.append(f"Type: {event.event_type} | Location: {event.location}")
        parts.append(f"Date: {event.event_date.strftime('%Y-%m-%d')}")
        parts.append(f"Severity: {event.severity:.2f} | Confidence: {event.confidence:.2f}")

        if sectors:
            top = sorted(sectors, key=lambda s: abs(s.return_5d), reverse=True)[:3]
            parts.append("Top impacted sectors:")
            for s in top:
                parts.append(f"  {s.sector_name} ({s.etf_ticker}): {s.return_5d:+.2f}% ({s.direction.value})")

        if bullish:
            parts.append("Bullish stocks:")
            for s in bullish[:3]:
                parts.append(f"  {s['ticker']}: {s['return_5d']:+.2f}%")

        if bearish:
            parts.append("Bearish stocks:")
            for s in bearish[:3]:
                parts.append(f"  {s['ticker']}: {s['return_5d']:+.2f}%")

        return "\n".join(parts)
