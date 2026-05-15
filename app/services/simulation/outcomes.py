from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.logging_config import get_logger
from app.services.simulation.models import (
    InferredSector,
    OutcomeScenario,
    ParsedScenario,
    ScenarioDirection,
)

logger = get_logger(__name__)


class OutcomeGenerator:
    """Generates probabilistic outcome scenarios for a hypothetical event."""

    async def generate(
        self, scenario: ParsedScenario,
        sectors: List[InferredSector],
        top_k: int = 7,
    ) -> List[OutcomeScenario]:
        base_outcomes = self._build_base_outcomes(scenario, sectors)

        calibrated = self._calibrate_probabilities(base_outcomes, scenario, sectors)

        return calibrated[:top_k]

    def _build_base_outcomes(
        self, scenario: ParsedScenario,
        sectors: List[InferredSector],
    ) -> List[OutcomeScenario]:
        outcomes: List[OutcomeScenario] = []
        sev = scenario.severity_estimate
        event_type = scenario.event_type

        best_case = self._make_best_case(scenario, sectors, sev, event_type)
        outcomes.append(best_case)

        base_case = self._make_base_case(scenario, sectors, sev, event_type)
        outcomes.append(base_case)

        worst_case = self._make_worst_case(scenario, sectors, sev, event_type)
        outcomes.append(worst_case)

        tail_case = self._make_tail_case(scenario, sectors, sev, event_type)
        outcomes.append(tail_case)

        escalation_case = self._make_escalation_case(scenario, sectors, sev, event_type)
        outcomes.append(escalation_case)

        slow_burn = self._make_slow_burn_case(scenario, sectors, sev, event_type)
        outcomes.append(slow_burn)

        contrarian = self._make_contrarian_case(scenario, sectors, sev, event_type)
        outcomes.append(contrarian)

        return outcomes

    def _make_best_case(
        self, scenario: ParsedScenario,
        sectors: List[InferredSector],
        sev: float, event_type: str,
    ) -> OutcomeScenario:
        sector_impacts = [
            {
                "sector": s.sector_name,
                "direction": s.impact_direction,
                "magnitude": s.impact_magnitude * 0.6,
            }
            for s in sectors[:5]
        ]
        return OutcomeScenario(
            scenario_label="Best Case / Rapid Resolution",
            probability=0.15,
            direction=ScenarioDirection.NEUTRAL,
            market_return_5d=1.0 - sev * 0.3,
            market_return_30d=3.0 - sev * 0.2,
            sector_impacts=sector_impacts,
            narrative=(
                f"Rapid de-escalation of {scenario.title}. "
                f"Diplomatic channels produce a framework for resolution within 2-4 weeks. "
                f"Markets initially volatile but recover quickly on relief rally. "
                f"Affected sectors see mean reversion. {scenario.location} risk premium collapses."
            ),
            key_catalysts=[
                "Ceasefire / diplomatic breakthrough",
                "Coordinated international response",
                "Central bank liquidity backstop",
                "Rapid policy clarity",
            ],
        )

    def _make_base_case(
        self, scenario: ParsedScenario,
        sectors: List[InferredSector],
        sev: float, event_type: str,
    ) -> OutcomeScenario:
        direction = self._determine_base_direction(sectors)
        sector_impacts = [
            {
                "sector": s.sector_name,
                "direction": s.impact_direction,
                "magnitude": s.impact_magnitude,
            }
            for s in sectors[:6]
        ]
        return OutcomeScenario(
            scenario_label="Base Case / Protracted Uncertainty",
            probability=0.35,
            direction=direction,
            market_return_5d=-(sev * 0.5),
            market_return_30d=-(sev * 0.8),
            sector_impacts=sector_impacts,
            narrative=(
                f"Protracted resolution timeline for {scenario.title}. "
                f"Event drags on for 3-6 months with periodic escalation and de-escalation cycles. "
                f"Markets gradually price in prolonged uncertainty. "
                f"Defensive and commodity sectors outperform. Cyclicals underperform."
            ),
            key_catalysts=[
                "Stalemate with periodic escalation",
                "Gradual sanctions / tariff ramp",
                "Earnings guidance downgrades",
                "Central bank easing",
            ],
        )

    def _make_worst_case(
        self, scenario: ParsedScenario,
        sectors: List[InferredSector],
        sev: float, event_type: str,
    ) -> OutcomeScenario:
        sector_impacts = [
            {
                "sector": s.sector_name,
                "direction": "bearish" if s.impact_direction != "bearish" else "bearish",
                "magnitude": s.impact_magnitude * 1.4,
            }
            for s in sectors[:6]
        ]
        return OutcomeScenario(
            scenario_label="Worst Case / Severe Escalation",
            probability=0.20,
            direction=ScenarioDirection.BEARISH,
            market_return_5d=-(5.0 + sev * 1.0),
            market_return_30d=-(10.0 + sev * 1.5),
            sector_impacts=sector_impacts,
            narrative=(
                f"Significant escalation of {scenario.title} beyond initial scope. "
                f"Broader regional involvement, severe economic disruption, "
                f"potential for supply chain paralysis. "
                f"Risk-off dominates: sell cyclicals, buy gold and treasuries. "
                f"VIX surges to crisis levels. Central bank emergency intervention likely."
            ),
            key_catalysts=[
                "Military escalation / wider conflict",
                "Comprehensive sanctions regime",
                "Supply chain breakdown",
                "Credit market dislocation",
            ],
        )

    def _make_tail_case(
        self, scenario: ParsedScenario,
        sectors: List[InferredSector],
        sev: float, event_type: str,
    ) -> OutcomeScenario:
        sector_impacts = [
            {
                "sector": s.sector_name,
                "direction": "bearish",
                "magnitude": min(1.0, s.impact_magnitude * 1.8),
            }
            for s in sectors[:5]
        ]
        return OutcomeScenario(
            scenario_label="Tail Risk / Systemic Crisis",
            probability=0.10,
            direction=ScenarioDirection.BEARISH,
            market_return_5d=-(8.0 + sev * 1.2),
            market_return_30d=-(20.0 + sev * 1.5),
            sector_impacts=sector_impacts,
            narrative=(
                f"Systemic crisis triggered by {scenario.title}. "
                f"Credit markets freeze, EM contagion, potential sovereign default. "
                f"Major financial institution distress. "
                f"Unprecedented policy response required. "
                f"Gold and treasuries rally sharply. All risk assets sell off."
            ),
            key_catalysts=[
                "Systemic credit event",
                "Sovereign default cascade",
                "Major financial institution failure",
                "Global recession trigger",
            ],
        )

    def _make_escalation_case(
        self, scenario: ParsedScenario,
        sectors: List[InferredSector],
        sev: float, event_type: str,
    ) -> OutcomeScenario:
        sector_impacts = [
            {
                "sector": s.sector_name,
                "direction": "bullish" if s.impact_direction == "bullish" else "bearish",
                "magnitude": s.impact_magnitude * 1.2,
            }
            for s in sectors[:5]
        ]
        return OutcomeScenario(
            scenario_label="Escalation Then Resolution",
            probability=0.20,
            direction=ScenarioDirection.MIXED,
            market_return_5d=-(3.0 + sev * 0.5),
            market_return_30d=2.0 - sev * 0.1,
            sector_impacts=sector_impacts,
            narrative=(
                f"Initial sharp escalation of {scenario.title} causes panic selling, "
                f"followed by diplomatic resolution within 4-8 weeks. "
                f"Sharp V-shaped recovery. Astute investors can capture "
                f"significant alpha by buying during peak panic."
            ),
            key_catalysts=[
                "Initial overreaction",
                "Back-channel negotiations",
                "Third-party mediation",
                "Confidence-restoring policy action",
            ],
        )

    def _make_slow_burn_case(
        self, scenario: ParsedScenario,
        sectors: List[InferredSector],
        sev: float, event_type: str,
    ) -> OutcomeScenario:
        sector_impacts = [
            {
                "sector": s.sector_name,
                "direction": s.impact_direction,
                "magnitude": s.impact_magnitude * 0.8,
            }
            for s in sectors[:6]
        ]
        return OutcomeScenario(
            scenario_label="Slow Burn / Structural Shift",
            probability=0.12,
            direction=ScenarioDirection.MIXED,
            market_return_5d=-(sev * 0.2),
            market_return_30d=-(sev * 0.6),
            sector_impacts=sector_impacts,
            narrative=(
                f"Gradual structural transformation triggered by {scenario.title}. "
                f"No single dramatic event, but a slow erosion of the status quo over 6-18 months. "
                f"New regulatory frameworks emerge. Incumbent players lose market share "
                f"to disruptors and new entrants. Portfolio rotation from growth to value. "
                f"Winners and losers diverge significantly within affected sectors."
            ),
            key_catalysts=[
                "Regulatory framework changes",
                "Gradual market share shift",
                "New competitor emergence",
                "Consumer behavior permanent shift",
                "Supply chain restructuring",
            ],
        )

    def _make_contrarian_case(
        self, scenario: ParsedScenario,
        sectors: List[InferredSector],
        sev: float, event_type: str,
    ) -> OutcomeScenario:
        sector_impacts = [
            {
                "sector": s.sector_name,
                "direction": "bullish" if s.impact_direction == "bearish" else "bearish",
                "magnitude": s.impact_magnitude * 0.9,
            }
            for s in sectors[:5]
        ]
        return OutcomeScenario(
            scenario_label="Contrarian / Black Swan Reversal",
            probability=0.08,
            direction=ScenarioDirection.BULLISH,
            market_return_5d=-(sev * 0.3),
            market_return_30d=5.0 + sev * 0.5,
            sector_impacts=sector_impacts,
            narrative=(
                f"Counter-intuitive outcome where {scenario.title} triggers an unexpected positive catalyst. "
                f"The crisis forces long-overdue structural reforms, accelerates innovation, "
                f"or removes a persistent overhang. Markets initially sell off but then rally "
                f"sharply as the silver lining becomes apparent. Sectors initially deemed most "
                f"at risk become the biggest beneficiaries of the new paradigm."
            ),
            key_catalysts=[
                "Crisis-driven innovation acceleration",
                "Forced structural reform",
                "Market overshoot creates buying opportunity",
                "Unexpected policy response",
                "Competitive landscape reshuffling",
            ],
        )

    def _determine_base_direction(
        self, sectors: List[InferredSector],
    ) -> ScenarioDirection:
        bullish = sum(1 for s in sectors if s.impact_direction == "bullish")
        bearish = sum(1 for s in sectors if s.impact_direction == "bearish")
        if bullish > bearish + 1:
            return ScenarioDirection.BULLISH
        if bearish > bullish + 1:
            return ScenarioDirection.BEARISH
        return ScenarioDirection.MIXED

    def _calibrate_probabilities(
        self, outcomes: List[OutcomeScenario],
        scenario: ParsedScenario,
        sectors: List[InferredSector],
    ) -> List[OutcomeScenario]:
        sev = scenario.severity_estimate
        event_type = scenario.event_type

        for outcome in outcomes:
            if "Worst" in outcome.scenario_label or "Tail" in outcome.scenario_label:
                outcome.probability += sev * 0.01
            elif "Best" in outcome.scenario_label:
                outcome.probability -= sev * 0.005

        if event_type in ["war", "financial_crisis", "pandemic"]:
            for outcome in outcomes:
                if "Worst" in outcome.scenario_label:
                    outcome.probability += 0.05
                elif "Best" in outcome.scenario_label:
                    outcome.probability -= 0.03

        total = sum(o.probability for o in outcomes)
        if total > 0:
            for outcome in outcomes:
                outcome.probability = round(outcome.probability / total, 4)

        overall_bullish = sum(
            1 for s in sectors
            if s.impact_direction == "bullish" and s.impact_magnitude > 0.5
        )
        if overall_bullish > 2:
            for outcome in outcomes:
                if "Best" in outcome.scenario_label:
                    outcome.probability += 0.03
                elif "Worst" in outcome.scenario_label:
                    outcome.probability -= 0.02

        total = sum(o.probability for o in outcomes)
        if total > 0:
            for outcome in outcomes:
                outcome.probability = round(outcome.probability / total, 4)

        outcomes.sort(key=lambda o: o.probability, reverse=True)
        return outcomes
