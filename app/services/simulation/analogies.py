from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.logging_config import get_logger
from app.services.simulation.models import AnalogicalMatch, ParsedScenario

logger = get_logger(__name__)


class AnalogyFinder:
    """Finds historical analogues for a given scenario."""

    async def find(
        self, scenario: ParsedScenario, sectors: List[Any],
        top_k: int = 5, min_similarity: float = 0.2,
    ) -> List[AnalogicalMatch]:
        text = self._build_query_text(scenario)
        sector_etfs = {s.etf_ticker for s in sectors}

        scored: List[tuple] = []
        for analogue in HISTORICAL_ANALOGUES:
            score = self._compute_similarity(analogue, text, scenario.event_type, sector_etfs)
            if score >= min_similarity:
                scored.append((score, analogue))

        scored.sort(key=lambda x: x[0], reverse=True)

        analogues: List[AnalogicalMatch] = []
        for score, data in scored[:top_k]:
            analogues.append(AnalogicalMatch(
                event_title=data["event_title"],
                event_date=data["event_date"],
                event_type=data["event_type"],
                similarity_score=score,
                key_similarities=self._extract_similarities(data, text),
                key_differences=self._extract_differences(data, text),
                market_impact_description=data.get("description", ""),
                sectors_affected=data.get("sectors_affected", []),
                return_5d=data.get("spy_return_5d", 0),
                return_30d=data.get("spy_return_30d", 0),
                volatility_change=data.get("vix_change", 0),
            ))

        return analogues

    def _build_query_text(self, scenario: ParsedScenario) -> str:
        parts = [
            scenario.title, scenario.description, scenario.event_type,
            scenario.location,
        ]
        parts.extend(scenario.countries)
        parts.extend(scenario.actors)
        return " ".join(parts).lower()

    def _compute_similarity(
        self, analogue: Dict, text: str,
        event_type: str, sector_etfs: set,
    ) -> float:
        score = 0.0

        if analogue["event_type"] == event_type:
            score += 0.25

        country_matches = sum(1 for c in analogue.get("countries", []) if c.lower() in text)
        score += min(0.3, country_matches * 0.1)

        sector_matches = sum(1 for s in analogue.get("sectors_affected", []) if s in sector_etfs)
        score += min(0.25, sector_matches * 0.05)

        desc_words = set(analogue.get("description", "").lower().split())
        text_words = set(text.split())
        overlap = len(desc_words & text_words)
        score += min(0.2, overlap * 0.02)

        return min(1.0, score)

    def _extract_similarities(self, analogue: Dict, text: str) -> List[str]:
        sims = []
        countries = analogue.get("countries", [])
        matched = [c for c in countries if c.lower() in text]
        if matched:
            sims.append(f"Same geographic region: {', '.join(matched)}")
        if analogue.get("sectors_affected"):
            sims.append(f"Similar sector impact pattern")
        sims.append(f"Same event category: {analogue['event_type']}")
        return sims[:3]

    def _extract_differences(self, analogue: Dict, text: str) -> List[str]:
        return [
            "Different geopolitical context and alliances",
            "Different market regime and interest rate environment",
            "Different scale of global economic integration",
        ]


HISTORICAL_ANALOGUES: List[Dict[str, Any]] = [
    {
        "event_title": "Russia-Ukraine War (2022)",
        "event_date": "2022-02-24",
        "event_type": "war",
        "countries": ["Russia", "Ukraine", "USA", "EU", "NATO"],
        "sectors_affected": ["XLE", "XLI", "XLK", "XLP", "GLD", "USO"],
        "spy_return_5d": -2.5, "spy_return_30d": -1.8, "vix_change": 12.5,
        "description": "Major land war in Europe triggered sanctions, commodity shock, energy crisis",
    },
    {
        "event_title": "COVID-19 Pandemic (2020)",
        "event_date": "2020-03-11",
        "event_type": "pandemic",
        "countries": ["Global"],
        "sectors_affected": ["XLV", "XLK", "XLY", "XLP", "XLU"],
        "spy_return_5d": -8.0, "spy_return_30d": -12.5, "vix_change": 25.0,
        "description": "Global pandemic caused economic shutdown, massive stimulus, tech acceleration",
    },
    {
        "event_title": "US-China Trade War Escalation (2018)",
        "event_date": "2018-07-06",
        "event_type": "trade_dispute",
        "countries": ["USA", "China"],
        "sectors_affected": ["XLI", "XLB", "XLK", "XLY"],
        "spy_return_5d": -1.2, "spy_return_30d": -3.5, "vix_change": 4.0,
        "description": "Tariffs on $34B of Chinese goods triggered tit-for-tat escalation",
    },
    {
        "event_title": "Russian Financial Crisis (1998)",
        "event_date": "1998-08-17",
        "event_type": "financial_crisis",
        "countries": ["Russia"],
        "sectors_affected": ["XLF", "XLE", "GLD"],
        "spy_return_5d": -3.0, "spy_return_30d": -8.0, "vix_change": 15.0,
        "description": "Russian default and ruble devaluation triggered LTCM collapse",
    },
    {
        "event_title": "Hamas Attack on Israel (2023)",
        "event_date": "2023-10-07",
        "event_type": "war",
        "countries": ["Israel", "Palestine", "Iran", "USA"],
        "sectors_affected": ["XLE", "XLI", "XLF", "GLD", "USO"],
        "spy_return_5d": 0.5, "spy_return_30d": -2.0, "vix_change": 3.5,
        "description": "Surprise attack triggered regional conflict fears, oil spike, safe-haven flows",
    },
    {
        "event_title": "Iraq War (2003)",
        "event_date": "2003-03-20",
        "event_type": "war",
        "countries": ["USA", "Iraq", "UK"],
        "sectors_affected": ["XLE", "XLI", "XLF", "GLD"],
        "spy_return_5d": 1.5, "spy_return_30d": 3.0, "vix_change": -2.0,
        "description": "US-led invasion sparked oil price surge but market rallied on swift victory expectations",
    },
    {
        "event_title": "Iran Nuclear Deal Collapse (2018)",
        "event_date": "2018-05-08",
        "event_type": "sanctions",
        "countries": ["USA", "Iran"],
        "sectors_affected": ["XLE", "GLD", "USO"],
        "spy_return_5d": -0.5, "spy_return_30d": -1.0, "vix_change": 1.5,
        "description": "US withdrawal from JCPOA reimposed sanctions on Iran, oil supply concerns",
    },
    {
        "event_title": "Brexit Referendum (2016)",
        "event_date": "2016-06-23",
        "event_type": "election",
        "countries": ["UK", "EU"],
        "sectors_affected": ["XLF", "XLI", "XLY"],
        "spy_return_5d": -3.5, "spy_return_30d": 0.5, "vix_change": 8.0,
        "description": "UK voted to leave EU, triggering political chaos, sterling crash, global uncertainty",
    },
    {
        "event_title": "2008 Global Financial Crisis",
        "event_date": "2008-09-15",
        "event_type": "financial_crisis",
        "countries": ["USA", "Global"],
        "sectors_affected": ["XLF", "XLY", "XLRE", "XLI"],
        "spy_return_5d": -8.0, "spy_return_30d": -25.0, "vix_change": 30.0,
        "description": "Lehman Brothers collapse triggered systemic banking crisis, global recession",
    },
    {
        "event_title": "Crimea Annexation (2014)",
        "event_date": "2014-03-18",
        "event_type": "war",
        "countries": ["Russia", "Ukraine"],
        "sectors_affected": ["XLE", "GLD", "USO"],
        "spy_return_5d": 1.0, "spy_return_30d": 2.0, "vix_change": 2.0,
        "description": "Limited conflict and targeted sanctions had moderate market impact",
    },
    {
        "event_title": "OPEC+ Oil Price War (2020)",
        "event_date": "2020-03-08",
        "event_type": "trade_dispute",
        "countries": ["Saudi Arabia", "Russia"],
        "sectors_affected": ["XLE", "USO", "XLI"],
        "spy_return_5d": -5.0, "spy_return_30d": -10.0, "vix_change": 15.0,
        "description": "Saudi-Russia price war sent oil crashing 30% in one day, energy sector collapse",
    },
    {
        "event_title": "Taiwan Strait Crisis (2022)",
        "event_date": "2022-08-02",
        "event_type": "war",
        "countries": ["Taiwan", "China", "USA", "Japan"],
        "sectors_affected": ["XLK", "XLI", "XLE"],
        "spy_return_5d": -1.5, "spy_return_30d": -3.0, "vix_change": 4.0,
        "description": "Pelosi visit and Chinese military drills raised semiconductor supply fears",
    },
    {
        "event_title": "Arab Spring (2011)",
        "event_date": "2011-01-25",
        "event_type": "civil_unrest",
        "countries": ["Egypt", "Tunisia", "Libya", "Syria", "Yemen"],
        "sectors_affected": ["XLE", "GLD", "USO"],
        "spy_return_5d": -1.5, "spy_return_30d": 1.0, "vix_change": 4.0,
        "description": "Wave of protests across MENA region caused oil price spike, commodity volatility",
    },
    {
        "event_title": "Suez Canal Blockage (2021)",
        "event_date": "2021-03-23",
        "event_type": "natural_disaster",
        "countries": ["Egypt", "Global"],
        "sectors_affected": ["XLI", "XLP", "XLE"],
        "spy_return_5d": -0.8, "spy_return_30d": 1.0, "vix_change": 2.0,
        "description": "Ever Given blockage disrupted global shipping for 6 days, supply chain shock",
    },
    {
        "event_title": "Colonial Pipeline Cyberattack (2021)",
        "event_date": "2021-05-07",
        "event_type": "cyberattack",
        "countries": ["USA"],
        "sectors_affected": ["XLK", "XLE", "XLI"],
        "spy_return_5d": 1.0, "spy_return_30d": 3.0, "vix_change": 5.0,
        "description": "Ransomware attack on critical fuel pipeline caused regional supply disruption",
    },
    {
        "event_title": "North Korea Missile Tests (2017)",
        "event_date": "2017-09-03",
        "event_type": "war",
        "countries": ["North Korea", "South Korea", "USA", "Japan"],
        "sectors_affected": ["XLE", "GLD", "XLK"],
        "spy_return_5d": -1.0, "spy_return_30d": 1.5, "vix_change": 3.0,
        "description": "ICBM and nuclear test sparked safe-haven flows, regional defense buildup",
    },
]
