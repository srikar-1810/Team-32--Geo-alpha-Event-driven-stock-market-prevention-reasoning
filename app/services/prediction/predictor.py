from __future__ import annotations

import statistics
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.logging_config import get_logger
from app.services.historical.market_collector import SECTOR_TICKER_MAP
from app.services.prediction.models import (
    ConfidenceDecomposition,
    ConfidenceLevel,
    ContributionBreakdown,
    NaturalLanguageReasoning,
    PredictionDirection,
    PredictionResult,
    SectorPrediction,
    SignalContribution,
    StockPrediction,
    TimeHorizon,
    VolatilityWarning,
)
from app.services.prediction.signals import SignalAggregator
from app.services.tiingo.client import SECTOR_ETF_MAP

logger = get_logger(__name__)

SIGNAL_WEIGHTS: Dict[str, float] = {
    "news": 0.25,
    "social_sentiment": 0.20,
    "historical_analogy": 0.20,
    "market_momentum": 0.15,
    "volatility_regime": 0.20,
}


class PredictionEngine:
    """Core prediction engine with multi-signal fusion and explainability."""

    def __init__(self, signals: Optional[SignalAggregator] = None) -> None:
        self.signals = signals or SignalAggregator()

    async def predict(
        self,
        query: str,
        tickers: Optional[List[str]] = None,
        sectors: Optional[List[str]] = None,
    ) -> PredictionResult:
        """Generate full prediction with explanations for query/tickers/sectors."""
        start = time.perf_counter()
        logger.info("Prediction START: query=%s, tickers=%s, sectors=%s", query[:60], tickers, sectors)

        all_signals = await self.signals.compute_all_signals(query, tickers, sectors)

        sector_predictions = await self._predict_sectors(all_signals, sectors)
        stock_predictions = await self._predict_stocks(all_signals, tickers)

        bullish = sorted(
            [s.to_dict() for s in stock_predictions if s.direction == PredictionDirection.BULLISH],
            key=lambda x: x.get("confidence", 0), reverse=True,
        )[:5]

        bearish = sorted(
            [s.to_dict() for s in stock_predictions if s.direction == PredictionDirection.BEARISH],
            key=lambda x: x.get("confidence", 0), reverse=True,
        )[:5]

        vol_warnings = self._get_volatility_warnings(sector_predictions, stock_predictions, all_signals)

        overall_conf = self._compute_overall_confidence(sector_predictions, stock_predictions)

        outlook = self._generate_market_outlook(all_signals, sector_predictions)

        elapsed = (time.perf_counter() - start) * 1000
        logger.info(
            "Prediction COMPLETE: %d sectors, %d stocks, %.0fms",
            len(sector_predictions), len(stock_predictions), elapsed,
        )

        return PredictionResult(
            query=query,
            tickers=tickers or [],
            sectors=sectors or [],
            generated_at=datetime.now(timezone.utc).isoformat(),
            execution_time_ms=elapsed,
            sector_predictions=sector_predictions,
            stock_predictions=stock_predictions,
            top_bullish=bullish,
            top_bearish=bearish,
            high_volatility_warnings=vol_warnings,
            overall_market_outlook=outlook,
            overall_confidence=overall_conf,
        )

    async def _predict_sectors(
        self, all_signals: Dict[str, Any], sectors: Optional[List[str]] = None,
    ) -> List[SectorPrediction]:
        geo = all_signals.get("geopolitical", {})
        social = all_signals.get("social", {})
        historical = all_signals.get("historical", {})
        momentum = all_signals.get("momentum", {})
        volatility = all_signals.get("volatility", {})

        target_sectors = sectors or list(SECTOR_ETF_MAP.values())[:5]
        target_sectors = [s for s in target_sectors if s in SECTOR_ETF_MAP.values() or s in SECTOR_ETF_MAP.keys()]

        predictions: List[SectorPrediction] = []
        for sector in target_sectors:
            etf = self._sector_to_etf(sector)
            pred = self._compute_sector_prediction(sector, etf, geo, social, historical, momentum, volatility)
            predictions.append(pred)

        return predictions

    async def _predict_stocks(
        self, all_signals: Dict[str, Any], tickers: Optional[List[str]] = None,
    ) -> List[StockPrediction]:
        if not tickers:
            return []

        geo = all_signals.get("geopolitical", {})
        social = all_signals.get("social", {})
        historical = all_signals.get("historical", {})
        momentum = all_signals.get("momentum", {})
        volatility = all_signals.get("volatility", {})

        predictions: List[StockPrediction] = []
        for ticker in tickers:
            pred = self._compute_stock_prediction(ticker, geo, social, historical, momentum, volatility)
            predictions.append(pred)

        return predictions

    def _compute_sector_prediction(
        self, sector: str, etf: str,
        geo: Dict[str, Any], social: Dict[str, Any],
        historical: Dict[str, Any], momentum: Dict[str, Any],
        volatility: Dict[str, Any],
    ) -> SectorPrediction:
        contributions = self._compute_contributions_for_sector(sector, geo, social, historical, momentum, volatility)
        net = contributions.net_score()
        direction = self._score_to_direction(net)
        magnitude = abs(net) * 15.0

        momentum_data = momentum.get("sectors", {}).get(sector, {})
        hist_reactions = historical.get("market_reactions", {})

        pred_5d = magnitude * (1.0 if net > 0 else -1.0) * 0.7
        if direction == PredictionDirection.NEUTRAL:
            pred_5d = 0.0
        pred_30d = pred_5d * 2.5

        if momentum_data:
            mom_boost = momentum_data.get("momentum_10d", 0) * 0.15
            pred_5d += mom_boost
            pred_30d += mom_boost * 2.0

        if hist_reactions:
            hist_5d = hist_reactions.get("avg_market_return_5d", 0)
            if abs(hist_5d) > 1:
                pred_5d = (pred_5d + hist_5d * 0.3) / 1.3

        vol_data = volatility.get("overall", {})
        vix = vol_data.get("vix_close", 15)
        vol_warning = self._vix_to_warning(vix)
        if pred_5d > 0 and vol_warning in (VolatilityWarning.HIGH, VolatilityWarning.EXTREME):
            pred_5d *= 0.7

        sector_momentum = momentum_data.get("momentum_10d", 0)

        key_levels = self._compute_key_levels(etf, momentum_data)

        conf_decomp = self._decompose_confidence(contributions, net, vol_warning)
        reasoning = self._generate_sector_reasoning(sector, net, direction, contributions, vol_warning)

        return SectorPrediction(
            sector_name=sector,
            etf_ticker=etf,
            direction=direction,
            predicted_return_5d=round(pred_5d, 2),
            predicted_return_30d=round(pred_30d, 2),
            confidence=conf_decomp.overall_confidence,
            confidence_decomposition=conf_decomp,
            contributions=contributions,
            volatility_warning=vol_warning,
            reasoning=reasoning,
            key_levels=key_levels,
        )

    def _compute_stock_prediction(
        self, ticker: str,
        geo: Dict[str, Any], social: Dict[str, Any],
        historical: Dict[str, Any], momentum: Dict[str, Any],
        volatility: Dict[str, Any],
    ) -> StockPrediction:
        sector = self._ticker_to_sector(ticker)
        contributions = self._compute_contributions_for_stock(ticker, geo, social, historical, momentum, volatility)
        net = contributions.net_score()
        direction = self._score_to_direction(net)
        magnitude = abs(net) * 20.0

        ticker_momentum = momentum.get("tickers", {}).get(ticker, {})
        hist_reactions = historical.get("market_reactions", {})

        pred_5d = magnitude * (1.0 if net > 0 else -1.0) * 0.6
        if direction == PredictionDirection.NEUTRAL:
            pred_5d = 0.0
        pred_30d = pred_5d * 2.5

        if ticker_momentum:
            mom = ticker_momentum.get("momentum_10d", 0)
            rsi = ticker_momentum.get("rsi_14", 50)
            pred_5d += mom * 0.2
            if rsi > 70 and pred_5d > 0:
                pred_5d *= 0.6
            elif rsi < 30 and pred_5d < 0:
                pred_5d *= 0.6

        ticker_vol = volatility.get("tickers", {}).get(ticker, {})
        ann_vol = ticker_vol.get("annualized_volatility", 0.2)
        if ann_vol > 0.4:
            vol_warning = VolatilityWarning.HIGH
        elif ann_vol > 0.3:
            vol_warning = VolatilityWarning.ELEVATED
        elif ann_vol < 0.15:
            vol_warning = VolatilityWarning.LOW
        else:
            vol_warning = VolatilityWarning.NORMAL

        current_price = ticker_momentum.get("current_price", 0)
        price_targets = {}
        if current_price > 0 and abs(pred_5d) > 0.5:
            price_targets["5d_target"] = current_price * (1 + pred_5d / 100)
            price_targets["30d_target"] = current_price * (1 + pred_30d / 100)

        conf_decomp = self._decompose_confidence(contributions, net, vol_warning)

        if hist_reactions:
            bullish_hist = hist_reactions.get("most_common_bullish", [])
            bearish_hist = hist_reactions.get("most_common_bearish", [])
            bullish_tickers = [b["ticker"] for b in bullish_hist if isinstance(b, dict)]
            bearish_tickers = [b["ticker"] for b in bearish_hist if isinstance(b, dict)]
        else:
            bullish_tickers = []
            bearish_tickers = []

        reasoning = self._generate_stock_reasoning(ticker, net, direction, contributions, vol_warning, bullish_tickers, bearish_tickers)

        return StockPrediction(
            ticker=ticker,
            company_name="",
            sector=sector,
            direction=direction,
            predicted_return_5d=round(pred_5d, 2),
            predicted_return_30d=round(pred_30d, 2),
            confidence=conf_decomp.overall_confidence,
            confidence_decomposition=conf_decomp,
            contributions=contributions,
            volatility_warning=vol_warning,
            reasoning=reasoning,
            price_targets=price_targets,
        )

    def _compute_contributions_for_sector(
        self, sector: str,
        geo: Dict[str, Any], social: Dict[str, Any],
        historical: Dict[str, Any], momentum: Dict[str, Any],
        volatility: Dict[str, Any],
    ) -> ContributionBreakdown:
        geo_sectors = geo.get("sectors_mentioned", [])
        geo_relevant = 1.0 if sector in geo_sectors or any(s.lower() in geo.get("event_type_classification", "").lower() for s in [sector]) else 0.5
        geo_direction = self._str_to_direction(geo.get("direction", "neutral"))
        geo_strength = geo.get("signal_strength", 0.0) * geo_relevant
        geo_contrib = geo_strength * SIGNAL_WEIGHTS["news"] * (1.0 if geo_direction == PredictionDirection.BULLISH else -1.0 if geo_direction == PredictionDirection.BEARISH else 0.0)

        social_direction = self._str_to_direction(social.get("direction", "neutral"))
        social_strength = social.get("signal_strength", 0.0)
        social_contrib = social_strength * SIGNAL_WEIGHTS["social_sentiment"] * (1.0 if social_direction == PredictionDirection.BULLISH else -1.0 if social_direction == PredictionDirection.BEARISH else 0.0)

        hist_direction = self._str_to_direction(historical.get("direction", "neutral"))
        hist_strength = historical.get("signal_strength", 0.0)
        hist_contrib = hist_strength * SIGNAL_WEIGHTS["historical_analogy"] * (1.0 if hist_direction == PredictionDirection.BULLISH else -1.0 if hist_direction == PredictionDirection.BEARISH else 0.0)

        sector_momentum = momentum.get("sectors", {}).get(sector, {}).get("momentum_10d", 0)
        mom_strength = min(1.0, abs(sector_momentum) / 10.0)
        mom_direction = PredictionDirection.BULLISH if sector_momentum > 0 else PredictionDirection.BEARISH if sector_momentum < 0 else PredictionDirection.NEUTRAL
        mom_contrib = mom_strength * SIGNAL_WEIGHTS["market_momentum"] * (1.0 if mom_direction == PredictionDirection.BULLISH else -1.0 if mom_direction == PredictionDirection.BEARISH else 0.0)

        vol_warning = volatility.get("warning_level", "normal")
        vol_impact = {"extreme": -0.8, "high": -0.5, "elevated": -0.2, "normal": 0.0, "low": 0.1}.get(vol_warning, 0.0)
        vol_strength = abs(vol_impact)
        vol_direction = PredictionDirection.BEARISH if vol_impact < 0 else PredictionDirection.BULLISH if vol_impact > 0 else PredictionDirection.NEUTRAL
        vol_contrib = vol_strength * SIGNAL_WEIGHTS["volatility_regime"] * (1.0 if vol_direction == PredictionDirection.BULLISH else -1.0 if vol_direction == PredictionDirection.BEARISH else 0.0)

        return ContributionBreakdown(
            news_signal=SignalContribution("news", geo_direction, geo_contrib, SIGNAL_WEIGHTS["news"], geo_strength, geo.get("avg_severity", 0) / 10.0 if geo.get("avg_severity") else 0.0, f"Geopolitical event analysis ({geo.get('event_count', 0)} events)"),
            social_signal=SignalContribution("social_sentiment", social_direction, social_contrib, SIGNAL_WEIGHTS["social_sentiment"], social_strength, social.get("confidence", 0), f"Social sentiment from {social.get('post_count', 0)} posts"),
            historical_signal=SignalContribution("historical_analogy", hist_direction, hist_contrib, SIGNAL_WEIGHTS["historical_analogy"], hist_strength, historical.get("avg_similarity", 0), f"Historical analogues ({historical.get('analogue_count', 0)} similar events)"),
            momentum_signal=SignalContribution("market_momentum", mom_direction, mom_contrib, SIGNAL_WEIGHTS["market_momentum"], mom_strength, 0.0, f"Sector momentum {sector_momentum:+.2f}% (10d)"),
            volatility_signal=SignalContribution("volatility_regime", vol_direction, vol_contrib, SIGNAL_WEIGHTS["volatility_regime"], vol_strength, 0.0, f"Volatility regime: {vol_warning}"),
        )

    def _compute_contributions_for_stock(
        self, ticker: str,
        geo: Dict[str, Any], social: Dict[str, Any],
        historical: Dict[str, Any], momentum: Dict[str, Any],
        volatility: Dict[str, Any],
    ) -> ContributionBreakdown:
        sector = self._ticker_to_sector(ticker)
        sector_contribs = self._compute_contributions_for_sector(sector, geo, social, historical, momentum, volatility)

        ticker_mom = momentum.get("tickers", {}).get(ticker, {})
        mom_10d = ticker_mom.get("momentum_10d", 0)
        mom_strength = min(1.0, abs(mom_10d) / 12.0)
        mom_direction = PredictionDirection.BULLISH if mom_10d > 0 else PredictionDirection.BEARISH if mom_10d < 0 else PredictionDirection.NEUTRAL
        mom_contrib = mom_strength * SIGNAL_WEIGHTS["market_momentum"] * (1.0 if mom_direction == PredictionDirection.BULLISH else -1.0 if mom_direction == PredictionDirection.BEARISH else 0.0)

        return ContributionBreakdown(
            news_signal=sector_contribs.news_signal,
            social_signal=SignalContribution("social_sentiment", sector_contribs.social_signal.direction, sector_contribs.social_signal.contribution_score * 0.8, SIGNAL_WEIGHTS["social_sentiment"], sector_contribs.social_signal.signal_strength, sector_contribs.social_signal.confidence, f"Social sentiment for {ticker}'s sector ({sector})"),
            historical_signal=SignalContribution("historical_analogy", sector_contribs.historical_signal.direction, sector_contribs.historical_signal.contribution_score * 0.8, SIGNAL_WEIGHTS["historical_analogy"], sector_contribs.historical_signal.signal_strength, sector_contribs.historical_signal.confidence, f"Historical analogues for {ticker}'s sector"),
            momentum_signal=SignalContribution("market_momentum", mom_direction, mom_contrib, SIGNAL_WEIGHTS["market_momentum"], mom_strength, 0.0, f"Stock momentum {mom_10d:+.2f}% (10d)"),
            volatility_signal=sector_contribs.volatility_signal,
        )

    def _decompose_confidence(self, contributions: ContributionBreakdown, net_score: float, vol_warning: VolatilityWarning) -> ConfidenceDecomposition:
        signals = contributions.get_all_signals()
        active_signals = [s for s in signals if abs(s.contribution_score) > 0.01]

        if not active_signals:
            return ConfidenceDecomposition(
                overall_confidence=0.0, confidence_level=ConfidenceLevel.VERY_LOW,
                signal_agreement=0.0, data_quality_score=0.0,
                historical_precedent_strength=0.0, prediction_stability=0.0,
                uncertainty_range={"lower": -5.0, "upper": 5.0},
            )

        directions = [s.direction for s in active_signals]
        agreement = directions.count(max(directions, key=directions.count)) / len(directions)

        data_quality = sum(s.confidence * s.weight for s in signals) / sum(s.weight for s in signals) if sum(s.weight for s in signals) > 0 else 0

        hist_signal = contributions.historical_signal
        hist_strength = hist_signal.signal_strength * hist_signal.confidence

        signal_magnitudes = [abs(s.contribution_score) for s in active_signals]
        stability = 1.0 - (statistics.stdev(signal_magnitudes) / max(sum(signal_magnitudes) / len(signal_magnitudes), 0.001)) if len(signal_magnitudes) > 1 else 0.5
        stability = max(0.0, min(1.0, stability))

        vol_penalty = {"extreme": 0.5, "high": 0.3, "elevated": 0.15, "normal": 0.0, "low": -0.1}.get(vol_warning.value, 0.0)
        overall = (agreement * 0.25 + data_quality * 0.25 + hist_strength * 0.20 + stability * 0.15 + (1.0 - vol_penalty) * 0.15)
        overall = max(0.0, min(1.0, overall))

        if overall >= 0.85:
            level = ConfidenceLevel.VERY_HIGH
        elif overall >= 0.7:
            level = ConfidenceLevel.HIGH
        elif overall >= 0.5:
            level = ConfidenceLevel.MEDIUM
        elif overall >= 0.3:
            level = ConfidenceLevel.LOW
        else:
            level = ConfidenceLevel.VERY_LOW

        uncertainty_magnitude = (1.0 - overall) * 10.0
        return ConfidenceDecomposition(
            overall_confidence=round(overall, 4),
            confidence_level=level,
            signal_agreement=round(agreement, 4),
            data_quality_score=round(data_quality, 4),
            historical_precedent_strength=round(hist_strength, 4),
            prediction_stability=round(stability, 4),
            uncertainty_range={
                "lower": round(net_score * 15.0 - uncertainty_magnitude, 2),
                "upper": round(net_score * 15.0 + uncertainty_magnitude, 2),
            },
        )

    def _compute_overall_confidence(self, sector_preds: List[SectorPrediction], stock_preds: List[StockPrediction]) -> float:
        confidences = [s.confidence for s in sector_preds] + [s.confidence for s in stock_preds]
        return sum(confidences) / len(confidences) if confidences else 0.0

    def _generate_sector_reasoning(
        self, sector: str, net: float, direction: PredictionDirection,
        contributions: ContributionBreakdown, vol_warning: VolatilityWarning,
    ) -> NaturalLanguageReasoning:
        signals = contributions.get_all_signals()
        positive = [s for s in signals if s.contribution_score > 0.01]
        negative = [s for s in signals if s.contribution_score < -0.01]

        sorted_signals = sorted(signals, key=lambda s: abs(s.contribution_score), reverse=True)
        top_drivers = [f"{s.signal_name} ({s.description})" for s in sorted_signals[:3] if abs(s.contribution_score) > 0.01]

        risk_factors = []
        if vol_warning in (VolatilityWarning.HIGH, VolatilityWarning.EXTREME):
            risk_factors.append(f"Elevated volatility regime ({vol_warning.value}) increases downside risk")
        if negative:
            risk_factors.extend([f"{s.signal_name} signal is bearish ({s.contribution_score:.3f})" for s in negative[:2]])

        if direction == PredictionDirection.BULLISH:
            short = f"Bullish on {sector} driven by {len(positive)} positive signals"
            detailed = (
                f"The prediction for {sector} is {direction.value} with a net signal score of {net:.3f}. "
                f"Key bullish drivers: {', '.join(s.signal_name for s in positive[:3])}. "
                f"Bearish offsets: {', '.join(s.signal_name for s in negative[:2]) if negative else 'none'}. "
                f"Volatility regime is {vol_warning.value}, which {'caps' if vol_warning in (VolatilityWarning.HIGH, VolatilityWarning.EXTREME) else 'supports'} the outlook."
            )
        elif direction == PredictionDirection.BEARISH:
            short = f"Bearish on {sector} driven by {len(negative)} negative signals"
            detailed = (
                f"The prediction for {sector} is {direction.value} with a net signal score of {net:.3f}. "
                f"Key bearish drivers: {', '.join(s.signal_name for s in negative[:3])}. "
                f"Bullish offsets: {', '.join(s.signal_name for s in positive[:2]) if positive else 'none'}. "
                f"Volatility regime is {vol_warning.value}, amplifying the bearish outlook."
            )
        else:
            short = f"Neutral on {sector} — signals are mixed or weak"
            detailed = (
                f"The prediction for {sector} is neutral with a net signal score of {net:.3f}. "
                f"Bullish signals ({len(positive)}) and bearish signals ({len(negative)}) are roughly balanced. "
                f"Volatility regime is {vol_warning.value}."
            )

        return NaturalLanguageReasoning(
            short_summary=short,
            detailed_reasoning=detailed,
            key_drivers=top_drivers or ["No strong signal drivers"],
            risk_factors=risk_factors or ["No significant risk factors identified"],
            what_if_scenarios=self._generate_scenarios(net, vol_warning),
        )

    def _generate_stock_reasoning(
        self, ticker: str, net: float, direction: PredictionDirection,
        contributions: ContributionBreakdown, vol_warning: VolatilityWarning,
        bullish_hist: List[str], bearish_hist: List[str],
    ) -> NaturalLanguageReasoning:
        signals = contributions.get_all_signals()
        positive = [s for s in signals if s.contribution_score > 0.01]
        negative = [s for s in signals if s.contribution_score < -0.01]

        sorted_signals = sorted(signals, key=lambda s: abs(s.contribution_score), reverse=True)
        top_drivers = [f"{s.signal_name}" for s in sorted_signals[:3] if abs(s.contribution_score) > 0.01]

        risk_factors = []
        if vol_warning in (VolatilityWarning.HIGH, VolatilityWarning.EXTREME):
            risk_factors.append(f"High volatility regime increases execution risk for {ticker}")
        if ticker in bearish_hist:
            risk_factors.append(f"Historically underperformed during similar events")

        extra_bullish = f" Historical analogues show bullish patterns: {', '.join(bullish_hist[:3])}." if bullish_hist else ""
        extra_bearish = f" Historical analogues show bearish patterns: {', '.join(bearish_hist[:3])}." if bearish_hist else ""

        if direction == PredictionDirection.BULLISH:
            short = f"Bullish on {ticker} with {len(positive)} positive signal{'s' if len(positive) != 1 else ''}"
            detailed = f"{ticker} prediction is bullish (net={net:.3f}). Drivers: {', '.join(top_drivers)}.{extra_bullish}{extra_bearish} Volatility: {vol_warning.value}."
        elif direction == PredictionDirection.BEARISH:
            short = f"Bearish on {ticker} with {len(negative)} negative signal{'s' if len(negative) != 1 else ''}"
            detailed = f"{ticker} prediction is bearish (net={net:.3f}). Drivers: {', '.join(top_drivers)}.{extra_bullish}{extra_bearish} Volatility: {vol_warning.value}."
        else:
            short = f"Neutral on {ticker} — signals mixed"
            detailed = f"{ticker} prediction is neutral (net={net:.3f}). Bullish: {len(positive)}, Bearish: {len(negative)} signals.{extra_bullish}{extra_bearish}"

        return NaturalLanguageReasoning(
            short_summary=short,
            detailed_reasoning=detailed,
            key_drivers=top_drivers or ["No strong signal drivers"],
            risk_factors=risk_factors or ["No significant risk factors identified"],
            what_if_scenarios=self._generate_scenarios(net, vol_warning),
        )

    def _generate_scenarios(self, net: float, vol_warning: VolatilityWarning) -> List[str]:
        scenarios = []
        if net > 0.3:
            scenarios.append(f"If positive signals strengthen (+20%): return could be {abs(net) * 18:.1f}%")
            scenarios.append(f"If negative signals emerge unexpectedly: return could be {abs(net) * 5 - 10:.1f}%")
        elif net < -0.3:
            scenarios.append(f"If bearish signals intensify (-20%): return could be {abs(net) * -18:.1f}%")
            scenarios.append(f"If positive catalysts emerge: return could be {abs(net) * -5 + 10:.1f}%")
        else:
            scenarios.append("Breakout scenario: a strong catalyst could shift direction")
            scenarios.append("Mean reversion: continued mixed signals keep range-bound")

        if vol_warning in (VolatilityWarning.HIGH, VolatilityWarning.EXTREME):
            scenarios.append(f"Volatility shock: {vol_warning.value} volatility regime adds ±{(1.0 - abs(net)) * 15:.1f}% tail risk")

        return scenarios

    def _get_volatility_warnings(
        self, sector_preds: List[SectorPrediction],
        stock_preds: List[StockPrediction], all_signals: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        warnings = []
        for sp in sector_preds:
            if sp.volatility_warning in (VolatilityWarning.HIGH, VolatilityWarning.EXTREME, VolatilityWarning.ELEVATED):
                warnings.append({
                    "type": "sector",
                    "name": sp.sector_name,
                    "ticker": sp.etf_ticker,
                    "warning": sp.volatility_warning.value,
                    "reasoning": sp.reasoning.detailed_reasoning[:200],
                })
        for sp in stock_preds:
            if sp.volatility_warning in (VolatilityWarning.HIGH, VolatilityWarning.EXTREME, VolatilityWarning.ELEVATED):
                warnings.append({
                    "type": "stock",
                    "name": sp.ticker,
                    "ticker": sp.ticker,
                    "warning": sp.volatility_warning.value,
                    "reasoning": sp.reasoning.detailed_reasoning[:200],
                })

        vol = all_signals.get("volatility", {})
        vix_level = vol.get("vix_level", 0)
        if vix_level > 25:
            warnings.insert(0, {
                "type": "market",
                "name": "Broad Market",
                "ticker": "VIX",
                "warning": vol.get("warning_level", "elevated"),
                "reasoning": f"VIX at {vix_level:.1f} indicating elevated market fear",
            })

        return warnings

    def _generate_market_outlook(self, all_signals: Dict[str, Any], sector_preds: List[SectorPrediction]) -> str:
        bullish_count = sum(1 for s in sector_preds if s.direction == PredictionDirection.BULLISH)
        bearish_count = sum(1 for s in sector_preds if s.direction == PredictionDirection.BEARISH)
        total = len(sector_preds) or 1

        vol = all_signals.get("volatility", {})
        vix = vol.get("vix_level", 15)

        if bullish_count / total > 0.6 and vix < 20:
            return "Bullish market outlook with broad sector support and low volatility"
        elif bearish_count / total > 0.6:
            return f"Bearish outlook with {bearish_count}/{total} sectors negative"
        elif vix > 25:
            return f"Cautious outlook: VIX at {vix:.1f} suggests elevated uncertainty"
        else:
            return f"Mixed outlook: {bullish_count} bullish vs {bearish_count} bearish sectors"

    def _score_to_direction(self, score: float) -> PredictionDirection:
        if score > 0.05:
            return PredictionDirection.BULLISH
        elif score < -0.05:
            return PredictionDirection.BEARISH
        return PredictionDirection.NEUTRAL

    def _str_to_direction(self, s: str) -> PredictionDirection:
        if s.lower() in ("bullish", "positive", "greed"):
            return PredictionDirection.BULLISH
        elif s.lower() in ("bearish", "negative", "fear"):
            return PredictionDirection.BEARISH
        return PredictionDirection.NEUTRAL

    def _vix_to_warning(self, vix: float) -> VolatilityWarning:
        if vix > 35:
            return VolatilityWarning.EXTREME
        elif vix > 25:
            return VolatilityWarning.HIGH
        elif vix > 18:
            return VolatilityWarning.ELEVATED
        elif vix < 12:
            return VolatilityWarning.LOW
        return VolatilityWarning.NORMAL

    def _sector_to_etf(self, sector: str) -> str:
        reverse_map = {v.lower(): k for k, v in SECTOR_ETF_MAP.items()}
        return reverse_map.get(sector.lower(), sector)

    def _ticker_to_sector(self, ticker: str) -> str:
        for etf, tickers in SECTOR_TICKER_MAP.items():
            if ticker.upper() in tickers:
                return SECTOR_ETF_MAP.get(etf, "Unknown")
        return "Unknown"

    def _compute_key_levels(self, etf: str, momentum_data: Dict[str, Any]) -> List[float]:
        levels = []
        sma_20 = momentum_data.get("sma_20", 0)
        sma_50 = momentum_data.get("sma_50", 0)
        current = momentum_data.get("current_price", 0) or momentum_data.get("sma_20", 0)

        if sma_20:
            levels.append(round(sma_20, 2))
        if sma_50:
            levels.append(round(sma_50, 2))
        if current and sma_20:
            levels.append(round(current * 1.05, 2))
            levels.append(round(current * 0.95, 2))

        return levels[:5]

    async def close(self) -> None:
        await self.signals.close()
