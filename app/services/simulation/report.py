from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from app.logging_config import get_logger
from app.services.simulation.models import (
    AnalogicalMatch,
    InferredSector,
    InferredStock,
    OutcomeScenario,
    ParsedScenario,
    RiskFactor,
    SimulationReport,
    SupplyChainImpact,
    VolatilityOutlook,
)
from app.utils.llm_client import create_llm_client
from app.config import settings
import json

logger = get_logger(__name__)

REPORT_PROMPT = """You are a senior geopolitical & macroeconomic strategist.
Synthesize the provided simulation data into a highly detailed, professional Intelligence Report.
Use premium analytical language. Provide deep second-order effects.

Respond strictly with a JSON object matching this structure:
{
  "title": "string (catchy, professional title)",
  "executive_summary": "string (2-3 paragraphs of deep macro analysis)",
  "scenario_context": "string (detailed context and assumptions)",
  "key_judgments": [
    {
      "judgment": "string",
      "confidence": 0.0-1.0,
      "detail": "string (1 paragraph explaining the reasoning and market impact)"
    }
  ],
  "sector_analysis": "string (narrative analysis of the sector impacts)",
  "supply_chain_risks": "string (narrative analysis of supply chain vulnerabilities)",
  "historical_context": "string (narrative analysis of analogies)",
  "risk_assessment": "string (narrative analysis of risks and volatility)",
  "outcome_scenarios": "string (narrative analysis of the probability-weighted outcomes)",
  "recommendations": ["string (actionable, specific portfolio adjustments)", "string"],
  "confidence_assessment": "string (assessment of the simulation's certainty)",
  "disclaimers": ["string"]
}
"""


class ReportGenerator:
    """Generates structured intelligence reports from simulation analysis."""

    async def generate(
        self,
        scenario: ParsedScenario,
        sectors: List[InferredSector],
        stocks: List[InferredStock],
        supply_chain: List[SupplyChainImpact],
        analogies: List[AnalogicalMatch],
        risk_factors: List[RiskFactor],
        volatility: VolatilityOutlook,
        outcomes: List[OutcomeScenario],
    ) -> SimulationReport:
        sev = scenario.severity_estimate

        # Attempt to generate a high-quality report using the LLM
        try:
            client = create_llm_client()
            prompt_data = {
                "scenario": scenario.to_dict(),
                "top_sectors": [s.to_dict() for s in sorted(sectors, key=lambda x: x.impact_magnitude, reverse=True)[:5]],
                "top_stocks": [s.to_dict() for s in sorted(stocks, key=lambda x: x.relevance_score, reverse=True)[:5]],
                "supply_chain": [s.to_dict() for s in supply_chain],
                "analogies": [a.to_dict() for a in analogies],
                "risk_factors": [r.to_dict() for r in risk_factors],
                "volatility": volatility.to_dict(),
                "outcomes": [o.to_dict() for o in outcomes]
            }
            
            response = await client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": REPORT_PROMPT},
                    {"role": "user", "content": f"Generate the intelligence report based on this raw simulation data:\n\n{json.dumps(prompt_data)}"}
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            
            text = response.choices[0].message.content or "{}"
            if text.startswith("```json"):
                text = text.replace("```json", "", 1).strip()
            if text.startswith("```"):
                text = text.replace("```", "", 1).strip()
            if text.endswith("```"):
                text = text[:-3].strip()
            data = json.loads(text)
            
            return SimulationReport(
                title=data.get("title", f"Geopolitical Intelligence Report: {scenario.title}"),
                executive_summary=data.get("executive_summary", self._generate_executive_summary(scenario, sev, sectors, outcomes)),
                scenario_context=data.get("scenario_context", self._generate_scenario_context(scenario, sev)),
                key_judgments=data.get("key_judgments", self._generate_key_judgments(scenario, sectors, risk_factors, volatility)),
                sector_analysis=data.get("sector_analysis", self._generate_sector_analysis(sectors, stocks)),
                stock_picks=self._generate_stock_picks(stocks, sectors), # Keep deterministic
                supply_chain_risks=data.get("supply_chain_risks", self._generate_supply_chain_text(supply_chain)),
                historical_context=data.get("historical_context", self._generate_historical_context(analogies)),
                risk_assessment=data.get("risk_assessment", self._generate_risk_text(risk_factors, volatility)),
                outcome_scenarios=data.get("outcome_scenarios", self._generate_outcome_text(outcomes)),
                recommendations=data.get("recommendations", self._generate_recommendations(scenario, sectors, outcomes, volatility)),
                confidence_assessment=data.get("confidence_assessment", self._generate_confidence_assessment(sectors, risk_factors, analogies)),
                disclaimers=data.get("disclaimers", self._generate_disclaimers()),
            )

        except Exception as e:
            logger.warning("LLM report generation failed, falling back to deterministic generation: %s", e)
            
            executive_summary = self._generate_executive_summary(scenario, sev, sectors, outcomes)
            scenario_context = self._generate_scenario_context(scenario, sev)
            key_judgments = self._generate_key_judgments(scenario, sectors, risk_factors, volatility)
            sector_analysis = self._generate_sector_analysis(sectors, stocks)
            stock_picks = self._generate_stock_picks(stocks, sectors)
            supply_chain_risks = self._generate_supply_chain_text(supply_chain)
            historical_context = self._generate_historical_context(analogies)
            risk_assessment = self._generate_risk_text(risk_factors, volatility)
            outcome_scenarios = self._generate_outcome_text(outcomes)
            recommendations = self._generate_recommendations(scenario, sectors, outcomes, volatility)
            confidence_assessment = self._generate_confidence_assessment(sectors, risk_factors, analogies)
            disclaimers = self._generate_disclaimers()

            return SimulationReport(
                title=f"Geopolitical Intelligence Report: {scenario.title}",
                executive_summary=executive_summary,
                scenario_context=scenario_context,
                key_judgments=key_judgments,
                sector_analysis=sector_analysis,
                stock_picks=stock_picks,
                supply_chain_risks=supply_chain_risks,
                historical_context=historical_context,
                risk_assessment=risk_assessment,
                outcome_scenarios=outcome_scenarios,
                recommendations=recommendations,
                confidence_assessment=confidence_assessment,
                disclaimers=disclaimers,
            )

    def _generate_executive_summary(
        self, scenario: ParsedScenario, sev: float,
        sectors: List[InferredSector],
        outcomes: List[OutcomeScenario],
    ) -> str:
        top_sectors = sorted(sectors, key=lambda s: s.impact_magnitude, reverse=True)[:3]
        top_outcome = outcomes[0] if outcomes else None

        return (
            f"Scenario: {scenario.title}. "
            f"Severity assessment: {sev:.1f}/10. "
            f"Event type: {scenario.event_type}. "
            f"Scope: {scenario.economic_scope}. "
            f"Top affected sectors: {', '.join(s.sector_name for s in top_sectors)}. "
            f"Most likely outcome ({top_outcome.scenario_label if top_outcome else 'N/A'}): "
            f"{top_outcome.probability:.0%} probability. "
            f"Market direction: {top_outcome.direction.value if top_outcome else 'mixed'}. "
            f"Estimated 30-day market impact: "
            f"{top_outcome.market_return_30d:+.1f}% (SPY). "
            f"Recommended posture: {self._determine_posture(sectors, outcomes)}."
        )

    def _generate_scenario_context(
        self, scenario: ParsedScenario, sev: float,
    ) -> str:
        timeline_map = {
            "immediate": "hours to days",
            "short_term": "days to weeks",
            "medium_term": "weeks to months",
            "long_term": "months to years",
        }
        timeline_str = timeline_map.get(scenario.estimated_timeline, "unknown")

        return (
            f"Scenario analysis for: {scenario.title}\n\n"
            f"Description: {scenario.description}\n\n"
            f"Location: {scenario.location}\n"
            f"Countries involved: {', '.join(scenario.countries) if scenario.countries else 'N/A'}\n"
            f"Key actors: {', '.join(scenario.actors) if scenario.actors else 'N/A'}\n"
            f"Estimated severity: {sev:.1f}/10\n"
            f"Expected timeline: {scenario.estimated_timeline} ({timeline_str})\n"
            f"Economic scope: {scenario.economic_scope}\n"
            f"Uncertainty factors: {', '.join(scenario.uncertainty_factors)}"
        )

    def _generate_key_judgments(
        self, scenario: ParsedScenario,
        sectors: List[InferredSector],
        risk_factors: List[RiskFactor],
        volatility: VolatilityOutlook,
    ) -> List[Dict[str, Any]]:
        judgments: List[Dict[str, Any]] = []

        top_sectors = sorted(sectors, key=lambda s: s.impact_magnitude, reverse=True)[:3]
        if top_sectors:
            judgments.append({
                "judgment": "Sector Impact Concentration",
                "confidence": sum(s.confidence for s in top_sectors) / max(len(top_sectors), 1),
                "detail": (
                    f"Impact concentrated in {', '.join(s.sector_name for s in top_sectors)}. "
                    f"Highest conviction: {top_sectors[0].sector_name} ({top_sectors[0].impact_direction}, "
                    f"magnitude {top_sectors[0].impact_magnitude:.2f})."
                ),
            })
        else:
            judgments.append({
                "judgment": "Sector Impact Concentration",
                "confidence": 0.5,
                "detail": "No specific sector concentration identified for this scenario.",
            })

        top_risk = max(risk_factors, key=lambda r: r.severity) if risk_factors else None
        if top_risk:
            judgments.append({
                "judgment": f"Primary Risk: {top_risk.risk_factor}",
                "confidence": 1.0 - top_risk.probability,
                "detail": (
                    f"Severity: {top_risk.severity:.2f}, Probability: {top_risk.probability:.0%}. "
                    f"{top_risk.impact_description}"
                ),
            })

        judgments.append({
            "judgment": "Volatility Regime",
            "confidence": 0.7,
            "detail": (
                f"Expected VIX regime: {volatility.expected_regime}. "
                f"Estimated vol expansion: {volatility.estimated_vol_expansion:.1f}. "
                f"{volatility.vix_implication}"
            ),
        })

        return judgments

    def _generate_sector_analysis(
        self, sectors: List[InferredSector],
        stocks: List[InferredStock],
    ) -> str:
        if not sectors:
            return "No sector analysis available."

        lines = ["Sector Impact Analysis:", ""]
        for s in sorted(sectors, key=lambda x: x.impact_magnitude, reverse=True):
            sign = "+" if s.impact_direction == "bullish" else "-" if s.impact_direction == "bearish" else "~"
            sector_stocks = [st for st in stocks if st.etf_ticker == s.etf_ticker]
            stock_str = f" (stocks: {', '.join(st.ticker for st in sector_stocks[:4])})" if sector_stocks else ""
            lines.append(
                f"  {sign} {s.sector_name} ({s.etf_ticker}): "
                f"{s.impact_direction}, mag={s.impact_magnitude:.2f}, conf={s.confidence:.0%}"
                f"{stock_str}"
            )
            lines.append(f"    Reasoning: {s.reasoning}")

        lines.append("")
        lines.append("Note: Impact magnitudes range 0-1. Confidence reflects model certainty.")
        return "\n".join(lines)

    def _generate_stock_picks(
        self, stocks: List[InferredStock],
        sectors: List[InferredSector],
    ) -> List[Dict[str, Any]]:
        if not stocks:
            return [{"note": "No specific stock recommendations generated."}]

        picks: List[Dict[str, Any]] = []
        for st in sorted(stocks, key=lambda s: s.relevance_score, reverse=True)[:10]:
            sector = next((s for s in sectors if s.etf_ticker == st.etf_ticker), None)
            picks.append({
                "ticker": st.ticker,
                "company": st.company_name or st.ticker,
                "sector": sector.sector_name if sector else st.sector,
                "exposure": st.exposure_type,
                "relevance": st.relevance_score,
                "expected_direction": sector.impact_direction if sector else "neutral",
                "reasoning": st.reasoning,
            })
        return picks

    def _generate_supply_chain_text(
        self, supply_chain: List[SupplyChainImpact],
    ) -> str:
        if not supply_chain:
            return "No significant supply chain impacts identified."

        lines = ["Supply Chain Risk Assessment:", ""]
        for sc in supply_chain:
            lines.append(
                f"  [{sc.impact_severity.value.upper()}] {sc.node}: "
                f"{sc.estimated_disruption_days} days disruption est."
            )
            lines.append(f"    {sc.description}")
            if sc.affected_companies:
                lines.append(f"    Companies: {', '.join(sc.affected_companies)}")
            lines.append(f"    Confidence: {sc.confidence:.0%}")
        return "\n".join(lines)

    def _generate_historical_context(
        self, analogies: List[AnalogicalMatch],
    ) -> str:
        if not analogies:
            return "No close historical analogues identified."

        lines = ["Historical Analogues:", ""]
        for a in analogies:
            lines.append(
                f"  [{a.similarity_score:.0%} match] {a.event_title} ({a.event_date})"
            )
            lines.append(f"    Similarities: {', '.join(a.key_similarities[:2])}")
            lines.append(f"    SPY 5d: {a.return_5d:+.1f}%, 30d: {a.return_30d:+.1f}%")
            lines.append(f"    VIX change: {a.volatility_change:+.1f}")
            if a.market_impact_description:
                lines.append(f"    Market impact: {a.market_impact_description}")
        return "\n".join(lines)

    def _generate_risk_text(
        self, risk_factors: List[RiskFactor],
        volatility: VolatilityOutlook,
    ) -> str:
        lines = ["Risk Assessment:", ""]
        for rf in sorted(risk_factors, key=lambda r: r.severity, reverse=True):
            lines.append(
                f"  [{rf.severity:.2f}] {rf.risk_factor} (prob: {rf.probability:.0%})"
            )
            lines.append(f"    {rf.impact_description}")
            lines.append(f"    Amplification: {rf.scenario_amplification}")

        lines.append("")
        lines.append(f"Volatility Outlook: {volatility.expected_regime}")
        lines.append(f"  {volatility.vix_implication}")
        lines.append(f"  Tail risk: {volatility.tail_risk_assessment}")
        if volatility.sector_divergences:
            lines.append("  Sector divergences:")
            for d in volatility.sector_divergences:
                lines.append(f"    - {d}")
        return "\n".join(lines)

    def _generate_outcome_text(
        self, outcomes: List[OutcomeScenario],
    ) -> str:
        lines = ["Outcome Scenarios (probability-weighted):", ""]
        for o in sorted(outcomes, key=lambda x: x.probability, reverse=True):
            lines.append(
                f"  [{o.probability:.0%}] {o.scenario_label} ({o.direction.value})"
            )
            lines.append(f"    Market (SPY): 5d={o.market_return_5d:+.1f}%, 30d={o.market_return_30d:+.1f}%")
            lines.append(f"    {o.narrative[:150]}...")
            if o.key_catalysts:
                lines.append(f"    Catalysts: {', '.join(o.key_catalysts[:3])}")
        return "\n".join(lines)

    def _generate_recommendations(
        self, scenario: ParsedScenario,
        sectors: List[InferredSector],
        outcomes: List[OutcomeScenario],
        volatility: VolatilityOutlook,
    ) -> List[str]:
        recs: List[str] = []

        bullish_sectors = [s for s in sectors if s.impact_direction == "bullish"]
        bearish_sectors = [s for s in sectors if s.impact_direction == "bearish"]

        if bullish_sectors:
            recs.append(
                f"Overweight {bullish_sectors[0].sector_name} ({bullish_sectors[0].etf_ticker}) "
                f"for ~3-6 month horizon"
            )
        if bearish_sectors:
            recs.append(
                f"Underweight / hedge {bearish_sectors[0].sector_name} ({bearish_sectors[0].etf_ticker}) "
                f"exposure"
            )

        if volatility.expected_regime in ("crisis", "elevated"):
            recs.append(
                f"Implement tail hedging: consider VIX calls, put spreads on SPY. "
                f"Expected vol expansion: {volatility.estimated_vol_expansion:.0f}"
            )
        else:
            recs.append("Standard portfolio hedging sufficient given expected vol regime")

        recs.append("Maintain cash reserves for opportunity during drawdowns")
        recs.append("Monitor GDELT and Reddit signals for real-time event evolution")

        top_outcome = max(outcomes, key=lambda o: o.probability) if outcomes else None
        if top_outcome:
            recs.append(
                f"Base case ({top_outcome.scenario_label}, {top_outcome.probability:.0%}): "
                f"position for {top_outcome.direction.value} scenario"
            )

        return recs[:6]

    def _generate_confidence_assessment(
        self, sectors: List[InferredSector],
        risk_factors: List[RiskFactor],
        analogies: List[AnalogicalMatch],
    ) -> str:
        avg_sector_conf = sum(s.confidence for s in sectors) / max(len(sectors), 1)
        analogy_conf = sum(a.similarity_score for a in analogies) / max(len(analogies), 1) if analogies else 0

        if avg_sector_conf > 0.7 and analogy_conf > 0.6:
            level = "Moderately High"
        elif avg_sector_conf > 0.5:
            level = "Moderate"
        else:
            level = "Low to Moderate"

        return (
            f"Confidence Level: {level}\n"
            f"Average sector confidence: {avg_sector_conf:.0%}\n"
            f"Historical analogue similarity: {analogy_conf:.0%}\n"
            f"Number of risk factors assessed: {len(risk_factors)}\n"
            f"Number of historical analogues: {len(analogies)}\n\n"
            f"Confidence is limited by the hypothetical nature of the scenario. "
            f"Actual outcomes depend on real-time developments."
        )

    def _generate_disclaimers(self) -> List[str]:
        return [
            "This analysis is generated by an AI system for informational purposes only.",
            "All scenarios are hypothetical and do not constitute investment advice.",
            "Past performance of historical analogues does not guarantee future results.",
            "Actual market outcomes depend on numerous factors not captured in this simulation.",
            "Consult a qualified financial advisor before making investment decisions.",
        ]

    def _determine_posture(
        self, sectors: List[InferredSector],
        outcomes: List[OutcomeScenario],
    ) -> str:
        bullish = sum(1 for s in sectors if s.impact_direction == "bullish")
        bearish = sum(1 for s in sectors if s.impact_direction == "bearish")

        top = max(outcomes, key=lambda o: o.probability) if outcomes else None
        if not top:
            return "neutral"

        if top.direction.value == "bearish" and bearish > bullish:
            return "defensive / risk-off"
        elif top.direction.value == "bullish" and bullish > bearish:
            return "offensive / risk-on"
        else:
            return "neutral / hedged"
