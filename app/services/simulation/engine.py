from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from uuid import uuid4
from datetime import datetime, timezone

from app.logging_config import get_logger
from app.services.simulation.models import (
    InferredSector,
    InferredStock,
    OutcomeScenario,
    ParsedScenario,
    RiskFactor,
    SimulationReport,
    SimulationResult,
    SupplyChainImpact,
    VolatilityOutlook,
)
from app.services.simulation.parser import ScenarioParser
from app.services.simulation.inference import SectorStockInferrer
from app.services.simulation.supply_chain import SupplyChainAnalyzer
from app.services.simulation.analogies import AnalogyFinder
from app.services.simulation.risk_vol import RiskVolatilityAssessor
from app.services.simulation.outcomes import OutcomeGenerator
from app.services.simulation.report import ReportGenerator

logger = get_logger(__name__)


class SimulationEngine:
    """Orchestrates the full simulation pipeline for what-if scenarios."""

    def __init__(
        self,
        parser: Optional[ScenarioParser] = None,
        inferrer: Optional[SectorStockInferrer] = None,
        supply_chain: Optional[SupplyChainAnalyzer] = None,
        analogies: Optional[AnalogyFinder] = None,
        risk_vol: Optional[RiskVolatilityAssessor] = None,
        outcomes: Optional[OutcomeGenerator] = None,
        report: Optional[ReportGenerator] = None,
    ) -> None:
        self._parser = parser or ScenarioParser()
        self._inferrer = inferrer or SectorStockInferrer()
        self._supply_chain = supply_chain or SupplyChainAnalyzer()
        self._analogies = analogies or AnalogyFinder()
        self._risk_vol = risk_vol or RiskVolatilityAssessor()
        self._outcomes = outcomes or OutcomeGenerator()
        self._report_gen = report or ReportGenerator()

    async def run(self, query: str) -> SimulationResult:
        logger.info("Simulation engine started for: %s", query[:80])
        start = time.monotonic()

        parsed = await self._parser.parse(query)
        logger.info("Scenario parsed: %s (type=%s, sev=%.1f)", parsed.title, parsed.event_type, parsed.severity_estimate)

        sectors, stocks = await self._inferrer.infer(parsed)
        logger.info("Sectors inferred: %d, Stocks inferred: %d", len(sectors), len(stocks))

        supply_chain_impacts = await self._supply_chain.analyze(parsed, sectors)
        logger.info("Supply chain impacts: %d", len(supply_chain_impacts))

        analogues = await self._analogies.find(parsed, sectors)
        logger.info("Historical analogues: %d", len(analogues))

        risk_factors, volatility = await self._risk_vol.assess(parsed, sectors)
        logger.info("Risk factors: %d, Vol regime: %s", len(risk_factors), volatility.expected_regime)

        outcome_scenarios = await self._outcomes.generate(parsed, sectors)
        logger.info("Outcome scenarios: %d", len(outcome_scenarios))

        report = await self._report_gen.generate(
            scenario=parsed,
            sectors=sectors,
            stocks=stocks,
            supply_chain=supply_chain_impacts,
            analogies=analogues,
            risk_factors=risk_factors,
            volatility=volatility,
            outcomes=outcome_scenarios,
        )
        logger.info("Report generated")

        elapsed = (time.monotonic() - start) * 1000

        top_bullish, top_bearish = self._compute_top_picks(sectors, stocks)
        overall_confidence = self._compute_overall_confidence(sectors, analogues, risk_factors)

        result = SimulationResult(
            simulation_id=str(uuid4()),
            query=query,
            created_at=datetime.now(timezone.utc).isoformat(),
            execution_time_ms=elapsed,
            parsed_scenario=parsed,
            sectors=sectors,
            stocks=stocks,
            supply_chain_impacts=supply_chain_impacts,
            analogies=analogues,
            risk_factors=risk_factors,
            volatility_outlook=volatility,
            outcomes=outcome_scenarios,
            report=report,
            top_bullish=top_bullish,
            top_bearish=top_bearish,
            overall_confidence=overall_confidence,
        )

        logger.info(
            "Simulation complete in %.0fms: %s | sev=%.1f | "
            "sectors=%d stocks=%d analogues=%d outcomes=%d",
            elapsed, parsed.title, parsed.severity_estimate,
            len(sectors), len(stocks), len(analogues), len(outcome_scenarios),
        )
        return result

    async def run_async(self, query: str) -> SimulationResult:
        return await self.run(query)

    def _compute_top_picks(
        self, sectors: List[InferredSector],
        stocks: List[InferredStock],
    ) -> tuple[List[Dict], List[Dict]]:
        bullish: List[Dict] = []
        bearish: List[Dict] = []

        for st in stocks:
            sector = next(
                (s for s in sectors if s.etf_ticker == st.etf_ticker),
                None,
            )
            direction = sector.impact_direction if sector else "neutral"
            entry = {
                "ticker": st.ticker,
                "company": st.company_name or st.ticker,
                "sector": sector.sector_name if sector else st.sector,
                "relevance": st.relevance_score,
                "direction": direction,
                "reasoning": st.reasoning,
            }
            if direction == "bullish":
                bullish.append(entry)
            elif direction == "bearish":
                bearish.append(entry)

        bullish.sort(key=lambda x: x["relevance"], reverse=True)
        bearish.sort(key=lambda x: x["relevance"], reverse=True)

        return bullish[:15], bearish[:15]

    def _compute_overall_confidence(
        self, sectors: List[InferredSector],
        analogues: list,
        risk_factors: List[RiskFactor],
    ) -> float:
        sector_conf = sum(s.confidence for s in sectors) / max(len(sectors), 1)
        analogy_conf = sum(getattr(a, "similarity_score", 0.5) for a in analogues) / max(len(analogues), 1)
        risk_conf = 1.0 - (sum(r.severity for r in risk_factors) / max(len(risk_factors), 1)) * 0.3

        return round(sector_conf * 0.4 + analogy_conf * 0.3 + risk_conf * 0.3, 4)

    async def health_check(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "engine": "SimulationEngine",
            "components": [
                "ScenarioParser",
                "SectorStockInferrer",
                "SupplyChainAnalyzer",
                "AnalogyFinder",
                "RiskVolatilityAssessor",
                "OutcomeGenerator",
                "ReportGenerator",
            ],
        }
