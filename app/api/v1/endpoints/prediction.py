from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.schemas.prediction import (
    ConfidenceDecompositionSchema,
    ContributionBreakdownSchema,
    NaturalLanguageReasoningSchema,
    PredictionExplainRequest,
    PredictionExplainResponse,
    PredictionRequest,
    PredictionResponse,
    SignalContributionSchema,
)
from app.core.dependencies import get_db_session, get_prediction_engine
from app.logging_config import get_logger
from app.services.prediction.predictor import PredictionEngine

logger = get_logger(__name__)
router = APIRouter()


@router.post("", response_model=PredictionResponse)
async def predict(
    payload: PredictionRequest,
    engine: PredictionEngine = Depends(get_prediction_engine),
    db=Depends(get_db_session),
):
    """Generate market predictions with full explainability for a geopolitical event."""
    try:
        result = await engine.predict(
            query=payload.query,
            tickers=payload.tickers,
            sectors=payload.sectors,
        )
        return PredictionResponse(**result.to_dict())
    except Exception as e:
        logger.error("Prediction failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/explain", response_model=PredictionExplainResponse)
async def explain_prediction(
    payload: PredictionExplainRequest,
    engine: PredictionEngine = Depends(get_prediction_engine),
    db=Depends(get_db_session),
):
    """Get detailed explainability for a specific ticker prediction."""
    try:
        result = await engine.predict(
            query=payload.query,
            tickers=[payload.ticker],
        )

        stock_pred = next(
            (s for s in result.stock_predictions if s.ticker == payload.ticker.upper()),
            None,
        )
        if not stock_pred:
            raise HTTPException(
                status_code=404,
                detail=f"No prediction available for {payload.ticker}",
            )

        return PredictionExplainResponse(
            ticker=stock_pred.ticker,
            contributions=ContributionBreakdownSchema(
                news_signal=SignalContributionSchema(**stock_pred.contributions.news_signal.to_dict()),
                social_signal=SignalContributionSchema(**stock_pred.contributions.social_signal.to_dict()),
                historical_signal=SignalContributionSchema(**stock_pred.contributions.historical_signal.to_dict()),
                momentum_signal=SignalContributionSchema(**stock_pred.contributions.momentum_signal.to_dict()),
                volatility_signal=SignalContributionSchema(**stock_pred.contributions.volatility_signal.to_dict()),
            ),
            confidence_decomposition=ConfidenceDecompositionSchema(
                overall_confidence=stock_pred.confidence_decomposition.overall_confidence,
                confidence_level=stock_pred.confidence_decomposition.confidence_level.value,
                signal_agreement=stock_pred.confidence_decomposition.signal_agreement,
                data_quality_score=stock_pred.confidence_decomposition.data_quality_score,
                historical_precedent_strength=stock_pred.confidence_decomposition.historical_precedent_strength,
                prediction_stability=stock_pred.confidence_decomposition.prediction_stability,
                uncertainty_range=stock_pred.confidence_decomposition.uncertainty_range,
            ),
            reasoning=NaturalLanguageReasoningSchema(
                short_summary=stock_pred.reasoning.short_summary,
                detailed_reasoning=stock_pred.reasoning.detailed_reasoning,
                key_drivers=stock_pred.reasoning.key_drivers,
                risk_factors=stock_pred.reasoning.risk_factors,
                what_if_scenarios=stock_pred.reasoning.what_if_scenarios,
            ),
            volatility_warning=stock_pred.volatility_warning.value,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Prediction explain failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))



