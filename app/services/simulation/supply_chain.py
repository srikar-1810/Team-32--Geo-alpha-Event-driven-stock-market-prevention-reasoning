from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.logging_config import get_logger
from app.services.simulation.models import (
    ParsedScenario,
    SupplyChainImpact,
    SupplyChainImpactSeverity,
)

logger = get_logger(__name__)

SUPPLY_CHAIN_NODES: Dict[str, Dict[str, Any]] = {
    "semiconductor_manufacturing": {
        "name": "Semiconductor Manufacturing",
        "regions": ["Taiwan", "South Korea", "China", "USA", "Japan"],
        "companies": ["TSM", "INTC", "AMD", "NVDA", "QCOM", "MU"],
        "sector_etf": "XLK",
    },
    "rare_earth_mining": {
        "name": "Rare Earth & Critical Minerals",
        "regions": ["China", "Australia", "USA", "Chile", "DRC"],
        "companies": ["MP", "LYSCF", "REE", "LAC", "SQM", "ALB"],
        "sector_etf": "XLB",
    },
    "oil_and_gas_production": {
        "name": "Oil & Gas Production",
        "regions": ["Saudi Arabia", "Russia", "USA", "Iran", "Iraq", "UAE"],
        "companies": ["XOM", "CVX", "COP", "OXY", "EOG", "SLB", "HAL"],
        "sector_etf": "XLE",
    },
    "automotive_manufacturing": {
        "name": "Automotive Manufacturing",
        "regions": ["Germany", "Japan", "USA", "China", "South Korea", "Mexico"],
        "companies": ["TSLA", "GM", "F", "TM", "HMC", "VWAGY", "BMWYY"],
        "sector_etf": "XLY",
    },
    "shipping_logistics": {
        "name": "Global Shipping & Logistics",
        "regions": ["China", "Singapore", "Netherlands", "Denmark", "USA"],
        "companies": ["FDX", "UPS", "ZIM", "DSX", "MATX", "GSL"],
        "sector_etf": "XLI",
    },
    "agricultural_commodities": {
        "name": "Agricultural Commodities",
        "regions": ["Ukraine", "Russia", "USA", "Brazil", "Argentina", "India"],
        "companies": ["ADM", "BG", "CTVA", "MON", "DE", "AGCO"],
        "sector_etf": "XLP",
    },
    "defense_contractors": {
        "name": "Defense Contractors",
        "regions": ["USA", "UK", "France", "Israel", "Germany"],
        "companies": ["LMT", "RTX", "NOC", "GD", "BA", "LHX"],
        "sector_etf": "XLI",
    },
    "technology_infrastructure": {
        "name": "Technology Infrastructure",
        "regions": ["USA", "China", "Ireland", "Singapore", "Japan"],
        "companies": ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "CRM"],
        "sector_etf": "XLK",
    },
    "energy_grid": {
        "name": "Energy Grid & Utilities",
        "regions": ["USA", "EU", "Russia", "China", "India"],
        "companies": ["NEE", "DUK", "SO", "D", "AEP", "EXC"],
        "sector_etf": "XLU",
    },
    "financial_infrastructure": {
        "name": "Financial Infrastructure",
        "regions": ["USA", "UK", "EU", "Switzerland", "Singapore"],
        "companies": ["JPM", "BAC", "C", "GS", "MS", "BLK", "ICE"],
        "sector_etf": "XLF",
    },
    "pharmaceuticals": {
        "name": "Pharmaceuticals & Biotech",
        "regions": ["USA", "EU", "India", "China", "Switzerland"],
        "companies": ["PFE", "JNJ", "MRK", "ABBV", "LLY", "BMY", "AMGN"],
        "sector_etf": "XLV",
    },
    "telecommunications": {
        "name": "Telecommunications & 5G",
        "regions": ["USA", "China", "South Korea", "EU", "Japan"],
        "companies": ["T", "VZ", "TMUS", "CSCO", "ERIC", "NOK"],
        "sector_etf": "XLC",
    },
    "construction_real_estate": {
        "name": "Construction & Real Estate",
        "regions": ["USA", "China", "UK", "Australia", "Canada"],
        "companies": ["DHI", "LEN", "PHM", "AMT", "PLD", "SPG"],
        "sector_etf": "XLRE",
    },
    "luxury_consumer": {
        "name": "Luxury Goods & Consumer Discretionary",
        "regions": ["France", "Italy", "USA", "China", "Japan"],
        "companies": ["LVMUY", "NKE", "SBUX", "MCD", "TJX", "ROST"],
        "sector_etf": "XLY",
    },
    "food_beverage": {
        "name": "Food & Beverage Processing",
        "regions": ["USA", "Brazil", "EU", "India", "China"],
        "companies": ["KO", "PEP", "MDLZ", "GIS", "K", "HSY"],
        "sector_etf": "XLP",
    },
    "cybersecurity": {
        "name": "Cybersecurity & Digital Defense",
        "regions": ["USA", "Israel", "UK", "Estonia", "Japan"],
        "companies": ["CRWD", "PANW", "FTNT", "ZS", "S", "OKTA"],
        "sector_etf": "XLK",
    },
    "gaming_entertainment": {
        "name": "Gaming & Digital Entertainment",
        "regions": ["USA", "Japan", "China", "South Korea", "EU"],
        "companies": ["ATVI", "EA", "TTWO", "RBLX", "U", "NTDOY", "SONY"],
        "sector_etf": "XLC",
    },
}


class SupplyChainAnalyzer:
    """Analyzes supply-chain impacts of hypothetical geopolitical events."""

    async def analyze(
        self, scenario: ParsedScenario, sectors: List[Any],
    ) -> List[SupplyChainImpact]:
        text = f"{scenario.title} {scenario.description} {scenario.event_type}".lower()
        text += f" {' '.join(scenario.countries).lower()} {' '.join(scenario.actors).lower()}"
        location_lower = scenario.location.lower()

        sector_names = {s.sector_name.lower() for s in sectors}
        sector_etfs = {s.etf_ticker for s in sectors}

        impacts: List[SupplyChainImpact] = []
        for node_id, node_info in SUPPLY_CHAIN_NODES.items():
            severity = self._compute_node_impact(
                node_id, node_info, text, location_lower,
                sector_names, sector_etfs, scenario.severity_estimate,
            )
            if severity != SupplyChainImpactSeverity.NONE:
                impacts.append(SupplyChainImpact(
                    node=node_info["name"],
                    impact_severity=severity,
                    description=self._generate_description(node_id, node_info, severity, scenario),
                    affected_companies=node_info["companies"][:5],
                    estimated_disruption_days=self._estimate_disruption(severity),
                    geographic_spread=node_info["regions"][:3],
                    confidence=self._compute_confidence(severity, scenario.severity_estimate),
                ))

        impacts.sort(key=lambda x: {"critical": 0, "severe": 1, "moderate": 2, "minor": 3, "none": 4}.get(x.impact_severity.value, 5))
        return impacts

    def _compute_node_impact(
        self, node_id: str, node_info: Dict, text: str,
        location: str, sector_names: set, sector_etfs: set,
        severity: float,
    ) -> SupplyChainImpactSeverity:
        etf = node_info["sector_etf"]
        base = SupplyChainImpactSeverity.NONE

        if etf in sector_etfs:
            base = SupplyChainImpactSeverity.MODERATE

        region_matches = sum(1 for r in node_info["regions"] if r.lower() in text or r.lower() in location)
        if region_matches > 0:
            if base == SupplyChainImpactSeverity.NONE:
                base = SupplyChainImpactSeverity.MINOR
            severity_boost = region_matches * 1
            if severity > 7 and region_matches > 1:
                base = SupplyChainImpactSeverity.CRITICAL
            elif severity > 5 and region_matches > 0:
                base = SupplyChainImpactSeverity.SEVERE if base == SupplyChainImpactSeverity.MODERATE else SupplyChainImpactSeverity.MODERATE

        company_matches = sum(1 for c in node_info["companies"] if c.lower() in text)
        if company_matches > 1 and base != SupplyChainImpactSeverity.NONE:
            levels = [SupplyChainImpactSeverity.CRITICAL, SupplyChainImpactSeverity.SEVERE,
                      SupplyChainImpactSeverity.MODERATE, SupplyChainImpactSeverity.MINOR]
            idx = levels.index(base) if base in levels else 3
            new_idx = max(0, idx - 1)
            base = levels[new_idx]

        return base

    def _generate_description(
        self, node_id: str, node_info: Dict,
        severity: SupplyChainImpactSeverity, scenario: ParsedScenario,
    ) -> str:
        sev_text = {
            SupplyChainImpactSeverity.CRITICAL: f"Critical disruption expected in {node_info['name']}. {scenario.event_type} directly threatens production in {', '.join(node_info['regions'][:2])}.",
            SupplyChainImpactSeverity.SEVERE: f"Severe impact on {node_info['name']} supply chain. Companies with exposure to {', '.join(node_info['regions'][:2])} at risk.",
            SupplyChainImpactSeverity.MODERATE: f"Moderate disruption likely in {node_info['name']}. Monitoring required for {', '.join(node_info['regions'][:2])} exposure.",
            SupplyChainImpactSeverity.MINOR: f"Minor impact on {node_info['name']}. Limited exposure to {', '.join(node_info['regions'][:2])}.",
            SupplyChainImpactSeverity.NONE: "",
        }
        return sev_text.get(severity, "")

    def _estimate_disruption(self, severity: SupplyChainImpactSeverity) -> int:
        mapping = {
            SupplyChainImpactSeverity.CRITICAL: 180,
            SupplyChainImpactSeverity.SEVERE: 90,
            SupplyChainImpactSeverity.MODERATE: 30,
            SupplyChainImpactSeverity.MINOR: 7,
            SupplyChainImpactSeverity.NONE: 0,
        }
        return mapping.get(severity, 0)

    def _compute_confidence(self, severity: SupplyChainImpactSeverity, raw_severity: float) -> float:
        base = {
            SupplyChainImpactSeverity.CRITICAL: 0.8,
            SupplyChainImpactSeverity.SEVERE: 0.7,
            SupplyChainImpactSeverity.MODERATE: 0.6,
            SupplyChainImpactSeverity.MINOR: 0.4,
            SupplyChainImpactSeverity.NONE: 0.0,
        }.get(severity, 0.5)
        return min(1.0, base * (raw_severity / 10.0 + 0.5))
