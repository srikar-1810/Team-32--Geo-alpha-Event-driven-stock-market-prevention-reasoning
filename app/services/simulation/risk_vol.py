from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.logging_config import get_logger
from app.services.simulation.models import (
    InferredSector,
    ParsedScenario,
    RiskFactor,
    VolatilityOutlook,
)

logger = get_logger(__name__)


class RiskVolatilityAssessor:
    """Assesses risk factors and volatility outlook for a scenario."""

    async def assess(
        self, scenario: ParsedScenario, sectors: List[InferredSector],
    ) -> tuple[List[RiskFactor], VolatilityOutlook]:
        risk_factors = self._assess_risk_factors(scenario, sectors)
        vol_outlook = self._assess_volatility(scenario, sectors, risk_factors)
        return risk_factors, vol_outlook

    def _assess_risk_factors(
        self, scenario: ParsedScenario, sectors: List[InferredSector],
    ) -> List[RiskFactor]:
        factors: List[RiskFactor] = []
        sev = scenario.severity_estimate

        escalation_risk = self._compute_escalation_risk(scenario)
        factors.append(escalation_risk)

        economic_contagion = self._compute_economic_contagion(scenario, sectors)
        factors.append(economic_contagion)

        policy_response = self._compute_policy_response_risk(scenario)
        factors.append(policy_response)

        supply_disruption = self._compute_supply_disruption_risk(scenario)
        factors.append(supply_disruption)

        market_liquidity = self._compute_liquidity_risk(scenario, sev)
        factors.append(market_liquidity)

        black_swan = self._compute_black_swan_risk(scenario, sev)
        factors.append(black_swan)

        sector_concentration = self._compute_sector_concentration(sectors)
        factors.append(sector_concentration)

        trade_disruption = self._compute_trade_disruption(scenario)
        factors.append(trade_disruption)

        factors.sort(key=lambda f: f.severity, reverse=True)
        return factors

    def _compute_escalation_risk(self, scenario: ParsedScenario) -> RiskFactor:
        sev = scenario.severity_estimate
        text = f"{scenario.title} {scenario.description}".lower()
        escalation_keywords = [
            "nuclear", "nato", "article 5", "escalation", "retaliation",
            "spiral", "proxy", "ally", "intervention", "regime change",
        ]
        kw_count = sum(1 for kw in escalation_keywords if kw in text)
        base_severity = min(1.0, sev / 10.0 + kw_count * 0.1)
        probability = min(0.9, 0.3 + sev / 20.0 + kw_count * 0.05)
        return RiskFactor(
            risk_factor="Escalation / Conflict Spiral",
            severity=base_severity,
            probability=probability,
            impact_description=(
                "Risk of broader regional or great-power escalation. "
                f"Estimated probability of escalation to wider conflict: {probability:.0%}"
            ),
            scenario_amplification=f"Each month of unresolved conflict increases escalation risk by ~15%. Monitor {', '.join(scenario.countries[:3])} response dynamics.",
        )

    def _compute_economic_contagion(
        self, scenario: ParsedScenario, sectors: List[InferredSector],
    ) -> RiskFactor:
        scope_mult = {"local": 0.3, "regional": 0.6, "global": 1.0}.get(scenario.economic_scope, 0.5)
        fin_exposure = any(s.etf_ticker in ["XLF", "HYG", "EEM"] for s in sectors)
        sev = scenario.severity_estimate
        base = scope_mult * (sev / 10.0)
        if fin_exposure:
            base *= 1.3
        return RiskFactor(
            risk_factor="Economic Contagion / Spillover",
            severity=min(1.0, base),
            probability=min(0.8, 0.2 + sev / 15.0),
            impact_description=(
                f"Risk of economic spillover beyond primary region. "
                f"Scope: {scenario.economic_scope}. "
                f"Financial sector exposure amplifies contagion channels."
            ),
            scenario_amplification="Monitor credit spreads (HYG), EM flows (EEM), and currency volatility for contagion signals.",
        )

    def _compute_policy_response_risk(
        self, scenario: ParsedScenario,
    ) -> RiskFactor:
        text = f"{scenario.title} {scenario.description}".lower()
        policy_keywords = [
            "sanctions", "tariff", "export control", "embargo", "nationalization",
            "expropriation", "capital control", "interest rate", "stimulus",
        ]
        kw_count = sum(1 for kw in policy_keywords if kw in text)
        sev = scenario.severity_estimate
        severity = min(1.0, 0.3 + kw_count * 0.1 + sev / 20.0)
        probability = min(0.9, 0.4 + kw_count * 0.08)
        return RiskFactor(
            risk_factor="Adverse Policy / Regulatory Response",
            severity=severity,
            probability=probability,
            impact_description=(
                f"Risk of significant policy intervention ({kw_count} policy signals detected). "
                f"Could include sanctions, tariffs, or capital controls."
            ),
            scenario_amplification="Policy responses often come in waves. First-round effects may be followed by retaliation and counter-measures.",
        )

    def _compute_supply_disruption_risk(
        self, scenario: ParsedScenario,
    ) -> RiskFactor:
        text = f"{scenario.title} {scenario.description}".lower()
        supply_keywords = [
            "supply chain", "shortage", "disruption", "logistics", "shipping",
            "commodity", "semiconductor", "chip", "energy", "food", "grain",
        ]
        kw_count = sum(1 for kw in supply_keywords if kw in text)
        sev = scenario.severity_estimate
        severity = min(1.0, 0.2 + kw_count * 0.12 + sev / 15.0)
        probability = min(0.85, 0.25 + kw_count * 0.1)
        return RiskFactor(
            risk_factor="Supply Chain / Commodity Disruption",
            severity=severity,
            probability=probability,
            impact_description=(
                f"Supply chain disruption risk ({kw_count} indicators detected). "
                f"Commodity price volatility and production bottlenecks likely."
            ),
            scenario_amplification="Supply disruptions typically persist 2-3x longer than the initial event. Inventory destocking amplifies price moves.",
        )

    def _compute_liquidity_risk(
        self, scenario: ParsedScenario, sev: float,
    ) -> RiskFactor:
        severity = min(1.0, sev / 12.0)
        probability = min(0.7, 0.1 + sev / 15.0)
        return RiskFactor(
            risk_factor="Market Liquidity / Funding Stress",
            severity=severity,
            probability=probability,
            impact_description=(
                "Potential for liquidity deterioration in affected markets. "
                "Wider bid-ask spreads, reduced depth, and funding pressure possible."
            ),
            scenario_amplification="Liquidity stress is most acute in EM currencies, high-yield credit, and small-cap equities.",
        )

    def _compute_black_swan_risk(
        self, scenario: ParsedScenario, sev: float,
    ) -> RiskFactor:
        severity = min(1.0, 0.1 + sev * 0.06)
        probability = min(0.3, 0.05 + sev / 40.0)
        return RiskFactor(
            risk_factor="Tail Risk / Black Swan",
            severity=severity,
            probability=probability,
            impact_description=(
                "Low-probability, high-impact tail risk. "
                "Scenario could trigger unforeseen chain reactions beyond base expectations."
            ),
            scenario_amplification="Monitor VIX term structure and credit default swaps for early warning signals.",
        )

    def _compute_sector_concentration(
        self, sectors: List[InferredSector],
    ) -> RiskFactor:
        high_conviction = [s for s in sectors if s.impact_magnitude > 0.7 and s.confidence > 0.6]
        severity = min(1.0, len(high_conviction) * 0.15)
        return RiskFactor(
            risk_factor="Sector Concentration / Crowded Trades",
            severity=severity,
            probability=min(0.6, 0.2 + len(high_conviction) * 0.05),
            impact_description=(
                f"{len(high_conviction)} sectors show high conviction impact. "
                "Consensus trades may reverse sharply if scenario evolves unexpectedly."
            ),
            scenario_amplification="Crowded positioning creates asymmetric downside risk. Monitor positioning data for excess.",
        )

    def _compute_trade_disruption(
        self, scenario: ParsedScenario,
    ) -> RiskFactor:
        text = f"{scenario.title} {scenario.description}".lower()
        trade_keywords = [
            "tariff", "trade", "export", "import", "quota", "protectionism",
            "dumping", "subsidy", "wto", "trade war",
        ]
        kw_count = sum(1 for kw in trade_keywords if kw in text)
        severity = min(1.0, kw_count * 0.15)
        probability = min(0.8, 0.1 + kw_count * 0.1)
        return RiskFactor(
            risk_factor="Trade / Tariff Disruption",
            severity=severity if severity > 0 else 0.1,
            probability=probability if probability > 0 else 0.05,
            impact_description=(
                f"Trade policy risk detected ({kw_count} indicators). "
                "Tariff escalation cycles can persist for multiple quarters."
            ),
            scenario_amplification="Trade disruptions compound through supply chains. First-order tariff impacts are often smaller than second-order uncertainty effects.",
        )

    def _assess_volatility(
        self, scenario: ParsedScenario,
        sectors: List[InferredSector],
        risk_factors: List[RiskFactor],
    ) -> VolatilityOutlook:
        sev = scenario.severity_estimate
        avg_risk = sum(f.severity for f in risk_factors) / max(len(risk_factors), 1)
        sector_div = self._compute_sector_divergence(sectors)

        vol_est = sev / 10.0 * avg_risk * 40.0
        vol_est = max(5.0, min(60.0, vol_est))

        if vol_est > 35:
            regime = "crisis"
            vix_text = f"VIX likely to spike to {vol_est:.0f}+ range. Significant hedging warranted."
            tail = "High tail risk. Consider deep out-of-the-money puts and VIX calls."
        elif vol_est > 20:
            regime = "elevated"
            vix_text = f"VIX expected in {vol_est:.0f}-{vol_est+10:.0f} range. Tail hedging recommended."
            tail = "Moderate tail risk. Monitor VIX futures curve for backwardation."
        elif vol_est > 12:
            regime = "moderate"
            vix_text = f"VIX likely in {vol_est:.0f}-{vol_est+5:.0f} range. Selective hedging."
            tail = "Low tail risk. Standard portfolio hedging sufficient."
        else:
            regime = "low"
            vix_text = f"VIX expected below {vol_est:.0f}. Minimal volatility premium."
            tail = "Very low tail risk. No special hedging needed."

        return VolatilityOutlook(
            expected_regime=regime,
            vix_implication=vix_text,
            sector_divergences=sector_div,
            estimated_vol_expansion=round(vol_est, 1),
            tail_risk_assessment=tail,
        )

    def _compute_sector_divergence(
        self, sectors: List[InferredSector],
    ) -> List[str]:
        divergences: List[str] = []
        bullish = [s for s in sectors if s.impact_direction == "bullish"]
        bearish = [s for s in sectors if s.impact_direction == "bearish"]

        if bullish and bearish:
            divergences.append(
                f"Strong divergence: {bullish[0].sector_name} (bullish) vs "
                f"{bearish[0].sector_name} (bearish)"
            )

        energy = next((s for s in sectors if s.etf_ticker == "XLE"), None)
        tech = next((s for s in sectors if s.etf_ticker == "XLK"), None)
        if energy and tech:
            dir_diff = "opposite" if energy.impact_direction != tech.impact_direction else "aligned"
            divergences.append(
                f"Energy ({energy.impact_direction}) and Tech ({tech.impact_direction}) "
                f"show {dir_diff} trajectories"
            )

        financial = next((s for s in sectors if s.etf_ticker == "XLF"), None)
        safe_haven = next((s for s in sectors if s.etf_ticker == "GLD"), None)
        if financial and safe_haven:
            divergences.append(
                f"Financials ({financial.impact_direction}) vs Gold ({safe_haven.impact_direction}) "
                "signal risk-off rotation potential"
            )

        return divergences[:4]
