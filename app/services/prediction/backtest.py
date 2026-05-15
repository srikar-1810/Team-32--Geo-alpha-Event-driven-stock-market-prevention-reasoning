"""Prediction backtesting engine: tests prediction accuracy against historical events."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.logging_config import get_logger
from app.services.prediction.models import (
    ConfidenceLevel,
    PredictionDirection,
    PredictionResult,
    SectorPrediction,
    StockPrediction,
)
from app.services.prediction.predictor import PredictionEngine
from app.services.prediction.signals import SignalAggregator

logger = get_logger(__name__)

DATA_DIR = Path("data/historical")


@dataclass
class BacktestResult:
    """Result of a backtest run."""
    total_events: int
    correct_direction: int
    incorrect_direction: int
    direction_accuracy: float
    mean_absolute_return_error_5d: float
    mean_absolute_return_error_30d: float
    mean_squared_error_5d: float
    mean_squared_error_30d: float
    sector_accuracy: Dict[str, Dict[str, Any]]
    confidence_calibration: List[Dict[str, Any]]
    predictions: List[Dict[str, Any]]
    actuals: List[Dict[str, Any]]
    execution_time_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_events": self.total_events,
            "correct_direction": self.correct_direction,
            "incorrect_direction": self.incorrect_direction,
            "direction_accuracy": round(self.direction_accuracy, 4),
            "mean_absolute_return_error_5d": round(self.mean_absolute_return_error_5d, 4),
            "mean_absolute_return_error_30d": round(self.mean_absolute_return_error_30d, 4),
            "mean_squared_error_5d": round(self.mean_squared_error_5d, 4),
            "mean_squared_error_30d": round(self.mean_squared_error_30d, 4),
            "sector_accuracy": self.sector_accuracy,
            "confidence_calibration": self.confidence_calibration,
            "predictions": self.predictions,
            "actuals": self.actuals,
            "execution_time_ms": round(self.execution_time_ms, 2),
        }


class PredictionBacktester:
    """Backtests prediction accuracy against historical geopolitical events."""

    def __init__(
        self,
        predictor: Optional[PredictionEngine] = None,
        signals: Optional[SignalAggregator] = None,
    ) -> None:
        self._predictor = predictor or PredictionEngine()
        self._signals = signals or SignalAggregator()

    async def run(
        self,
        max_events: int = 50,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        sector_filter: Optional[List[str]] = None,
        min_severity: float = 0.0,
    ) -> BacktestResult:
        start_time = datetime.now(timezone.utc)

        events = await self._load_events(
            max_events=max_events,
            start_date=start_date,
            end_date=end_date,
            min_severity=min_severity,
        )
        logger.info("Loaded %d historical events for backtest", len(events))

        predictions: List[Dict[str, Any]] = []
        actuals: List[Dict[str, Any]] = []
        correct_dir = 0
        incorrect_dir = 0
        sector_results: Dict[str, Dict[str, Any]] = {}

        for event in events:
            pred = await self._predict_for_event(event, sector_filter)
            actual = self._get_actuals(event)

            predictions.append(pred)
            actuals.append(actual)

            if pred["direction"] != "neutral" and actual["direction"] != "neutral":
                if pred["direction"] == actual["direction"]:
                    correct_dir += 1
                else:
                    incorrect_dir += 1

            self._update_sector_results(sector_results, pred, actual)

        total = correct_dir + incorrect_dir
        direction_acc = correct_dir / max(total, 1)

        mae_5d = self._compute_mae(predictions, actuals, "return_5d")
        mae_30d = self._compute_mae(predictions, actuals, "return_30d")
        mse_5d = self._compute_mse(predictions, actuals, "return_5d")
        mse_30d = self._compute_mse(predictions, actuals, "return_30d")

        calibration = self._compute_calibration(predictions, actuals)

        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        return BacktestResult(
            total_events=len(events),
            correct_direction=correct_dir,
            incorrect_direction=incorrect_dir,
            direction_accuracy=direction_acc,
            mean_absolute_return_error_5d=mae_5d,
            mean_absolute_return_error_30d=mae_30d,
            mean_squared_error_5d=mse_5d,
            mean_squared_error_30d=mse_30d,
            sector_accuracy=sector_results,
            confidence_calibration=calibration,
            predictions=predictions,
            actuals=actuals,
            execution_time_ms=elapsed,
        )

    async def _load_events(
        self,
        max_events: int,
        start_date: Optional[date],
        end_date: Optional[date],
        min_severity: float,
    ) -> List[Dict[str, Any]]:
        latest = DATA_DIR / "registry" / "latest.json"
        if not latest.exists():
            logger.warning("No historical dataset found. Run build_historical_dataset.py first.")
            return self._load_sample_events()

        try:
            meta = json.loads(latest.read_text())
            json_path = meta.get("file_paths", {}).get("json", "")
            if not json_path or not Path(json_path).exists():
                return self._load_sample_events()
            data = json.loads(Path(json_path).read_text())
        except Exception as e:
            logger.warning("Failed to load dataset: %s", e)
            return self._load_sample_events()

        end = end_date or date.today()
        start = start_date or (end - timedelta(days=365))

        filtered = []
        for item in data:
            ed = item.get("event_date", "")
            if not ed:
                continue
            try:
                ed_date = datetime.fromisoformat(ed).date()
            except (ValueError, TypeError):
                continue
            if ed_date < start or ed_date > end:
                continue
            if item.get("severity", 0) < min_severity:
                continue
            filtered.append(item)

        filtered.sort(key=lambda x: x.get("event_date", ""), reverse=True)
        return filtered[:max_events]

    def _load_sample_events(self) -> List[Dict[str, Any]]:
        logger.info("Using sample events for backtesting")
        return [
            {
                "event_id": "sample_001",
                "event_title": "Russia-Ukraine Escalation",
                "event_type": "war",
                "location": "Ukraine",
                "event_date": "2022-02-24",
                "severity": 8.5,
                "sectors_impacted": [
                    {"sector_name": "Energy", "etf_ticker": "XLE",
                     "return_5d": 8.5, "return_30d": 15.0},
                    {"sector_name": "Financials", "etf_ticker": "XLF",
                     "return_5d": -3.0, "return_30d": -5.0},
                ],
                "overall_market_return_5d": -2.5,
                "overall_market_return_30d": -1.8,
            },
            {
                "event_id": "sample_002",
                "event_title": "Fed Rate Decision",
                "event_type": "economic",
                "location": "United States",
                "event_date": "2022-03-16",
                "severity": 6.0,
                "sectors_impacted": [
                    {"sector_name": "Financials", "etf_ticker": "XLF",
                     "return_5d": 2.0, "return_30d": 4.0},
                    {"sector_name": "Technology", "etf_ticker": "XLK",
                     "return_5d": -1.5, "return_30d": -3.0},
                ],
                "overall_market_return_5d": 0.5,
                "overall_market_return_30d": 1.2,
            },
            {
                "event_id": "sample_003",
                "event_title": "Oil Supply Disruption",
                "event_type": "conflict",
                "location": "Middle East",
                "event_date": "2022-06-01",
                "severity": 7.0,
                "sectors_impacted": [
                    {"sector_name": "Energy", "etf_ticker": "XLE",
                     "return_5d": 5.0, "return_30d": 10.0},
                ],
                "overall_market_return_5d": -1.0,
                "overall_market_return_30d": -2.5,
            },
        ]

    async def _predict_for_event(
        self, event: Dict[str, Any],
        sector_filter: Optional[List[str]],
    ) -> Dict[str, Any]:
        event_date = event.get("event_date", "")
        sectors = event.get("sectors_impacted", [])
        query = event.get("event_title", "Historical event")

        tickers = []
        for s in sectors:
            etf = s.get("etf_ticker", "")
            if etf and (not sector_filter or etf in sector_filter):
                tickers.append(etf)

        if not tickers:
            tickers = ["SPY"]

        try:
            result = await self._predictor.generate_prediction(
                query=query,
                tickers=tickers,
                sectors=[],
                location=event.get("location", ""),
            )
        except Exception as e:
            logger.warning("Prediction failed for event %s: %s", event.get("event_id"), e)
            return {
                "event_id": event.get("event_id", ""),
                "event_title": event.get("event_title", ""),
                "direction": "neutral",
                "return_5d": 0.0,
                "return_30d": 0.0,
                "confidence": 0.0,
            }

        overall = self._aggregate_prediction_direction(result)
        return {
            "event_id": event.get("event_id", ""),
            "event_title": event.get("event_title", ""),
            "direction": overall["direction"],
            "return_5d": overall["return_5d"],
            "return_30d": overall["return_30d"],
            "confidence": overall["confidence"],
            "sector_predictions": [
                {
                    "sector": s.sector_name,
                    "etf": s.etf_ticker,
                    "direction": s.direction.value,
                    "return_5d": s.predicted_return_5d,
                    "return_30d": s.predicted_return_30d,
                    "confidence": s.confidence,
                }
                for s in result.sector_predictions
            ],
        }

    def _aggregate_prediction_direction(
        self, result: PredictionResult,
    ) -> Dict[str, Any]:
        if not result.sector_predictions:
            return {"direction": "neutral", "return_5d": 0.0, "return_30d": 0.0, "confidence": 0.0}

        avg_5d = sum(s.predicted_return_5d for s in result.sector_predictions) / len(result.sector_predictions)
        avg_30d = sum(s.predicted_return_30d for s in result.sector_predictions) / len(result.sector_predictions)
        avg_conf = sum(s.confidence for s in result.sector_predictions) / len(result.sector_predictions)

        if avg_5d > 1.0 and avg_30d > 2.0:
            direction = "bullish"
        elif avg_5d < -1.0 and avg_30d < -2.0:
            direction = "bearish"
        else:
            direction = "neutral"

        return {"direction": direction, "return_5d": avg_5d, "return_30d": avg_30d, "confidence": avg_conf}

    def _get_actuals(self, event: Dict[str, Any]) -> Dict[str, Any]:
        sectors = event.get("sectors_impacted", [])
        sectors_actual = []
        for s in sectors:
            sectors_actual.append({
                "sector": s.get("sector_name", ""),
                "etf": s.get("etf_ticker", ""),
                "return_5d": s.get("return_5d", 0),
                "return_30d": s.get("return_30d", 0),
            })

        avg_5d = event.get("overall_market_return_5d", 0)
        avg_30d = event.get("overall_market_return_30d", 0)

        if avg_5d > 1.0 and avg_30d > 2.0:
            direction = "bullish"
        elif avg_5d < -1.0 and avg_30d < -2.0:
            direction = "bearish"
        else:
            direction = "neutral"

        return {
            "event_id": event.get("event_id", ""),
            "event_title": event.get("event_title", ""),
            "direction": direction,
            "return_5d": avg_5d,
            "return_30d": avg_30d,
            "sectors": sectors_actual,
        }

    def _update_sector_results(
        self,
        results: Dict[str, Dict[str, Any]],
        pred: Dict[str, Any],
        actual: Dict[str, Any],
    ) -> None:
        pred_sectors = pred.get("sector_predictions", [])
        actual_sectors = actual.get("sectors", [])

        for ps in pred_sectors:
            etf = ps.get("etf", "")
            if not etf:
                continue
            if etf not in results:
                results[etf] = {"correct": 0, "incorrect": 0, "total": 0,
                                "sum_abs_error_5d": 0.0, "sum_abs_error_30d": 0.0}

            actual_sector = next(
                (a for a in actual_sectors if a.get("etf") == etf),
                None,
            )
            if actual_sector:
                results[etf]["total"] += 1
                pred_dir = ps.get("direction", "neutral")
                actual_dir = actual_sector.get("direction", "neutral") if isinstance(actual_sector, dict) else "neutral"
                if isinstance(actual_sector, dict):
                    results[etf]["sum_abs_error_5d"] += abs(
                        ps.get("return_5d", 0) - actual_sector.get("return_5d", 0)
                    )
                    results[etf]["sum_abs_error_30d"] += abs(
                        ps.get("return_30d", 0) - actual_sector.get("return_30d", 0)
                    )
                    if pred_dir != "neutral" and actual_dir == pred_dir:
                        results[etf]["correct"] += 1
                    elif pred_dir != "neutral":
                        results[etf]["incorrect"] += 1

    def _compute_mae(
        self, predictions: List[Dict], actuals: List[Dict], key: str,
    ) -> float:
        errors = []
        for p, a in zip(predictions, actuals):
            pe = p.get(key, 0)
            ae = a.get(key, 0)
            errors.append(abs(pe - ae))
        return sum(errors) / max(len(errors), 1) if errors else 0.0

    def _compute_mse(
        self, predictions: List[Dict], actuals: List[Dict], key: str,
    ) -> float:
        errors = []
        for p, a in zip(predictions, actuals):
            pe = p.get(key, 0)
            ae = a.get(key, 0)
            errors.append((pe - ae) ** 2)
        return sum(errors) / max(len(errors), 1) if errors else 0.0

    def _compute_calibration(
        self, predictions: List[Dict], actuals: List[Dict],
    ) -> List[Dict[str, Any]]:
        buckets = [(0.0, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 0.9), (0.9, 1.0)]
        calibration = []

        for lo, hi in buckets:
            bucket_preds = [
                (p, a) for p, a in zip(predictions, actuals)
                if lo <= p.get("confidence", 0) < hi
            ]
            if not bucket_preds:
                continue

            correct = sum(
                1 for p, a in bucket_preds
                if p.get("direction", "neutral") == a.get("direction", "neutral")
                and p.get("direction", "neutral") != "neutral"
            )
            total = sum(
                1 for p, a in bucket_preds
                if p.get("direction", "neutral") != "neutral"
            )
            accuracy = correct / max(total, 1)

            calibration.append({
                "confidence_bin": f"{lo:.0%}-{hi:.0%}",
                "count": len(bucket_preds),
                "accuracy": round(accuracy, 4),
                "avg_confidence": round((lo + hi) / 2, 4),
            })

        return calibration

    async def compare_models(
        self,
        models: Dict[str, PredictionEngine],
        max_events: int = 50,
    ) -> Dict[str, BacktestResult]:
        results = {}
        for name, predictor in models:
            backtester = PredictionBacktester(predictor=predictor)
            result = await backtester.run(max_events=max_events)
            results[name] = result
        return results
