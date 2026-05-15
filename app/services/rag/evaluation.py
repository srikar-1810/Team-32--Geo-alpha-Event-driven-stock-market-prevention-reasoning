from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Set, Tuple

from app.logging_config import get_logger

logger = get_logger(__name__)


class RetrievalEvaluator:
    """Evaluation metrics for historical event retrieval quality."""

    @staticmethod
    def precision_at_k(
        retrieved: List[Dict[str, Any]],
        relevant_ids: Set[str],
        k: int = 10,
    ) -> float:
        """Precision@K: fraction of retrieved documents that are relevant."""
        if k <= 0 or not retrieved:
            return 0.0
        top_k = retrieved[:k]
        relevant_count = sum(1 for r in top_k if r.get("event_id") in relevant_ids)
        return relevant_count / k

    @staticmethod
    def recall_at_k(
        retrieved: List[Dict[str, Any]],
        relevant_ids: Set[str],
        k: int = 10,
    ) -> float:
        """Recall@K: fraction of all relevant documents retrieved."""
        if not relevant_ids:
            return 0.0
        top_k = retrieved[:k]
        relevant_count = sum(1 for r in top_k if r.get("event_id") in relevant_ids)
        return relevant_count / len(relevant_ids)

    @staticmethod
    def f1_at_k(
        retrieved: List[Dict[str, Any]],
        relevant_ids: Set[str],
        k: int = 10,
    ) -> float:
        """F1@K: harmonic mean of precision and recall."""
        p = RetrievalEvaluator.precision_at_k(retrieved, relevant_ids, k)
        r = RetrievalEvaluator.recall_at_k(retrieved, relevant_ids, k)
        if p + r == 0:
            return 0.0
        return 2 * (p * r) / (p + r)

    @staticmethod
    def mean_reciprocal_rank(
        retrieved: List[Dict[str, Any]],
        relevant_ids: Set[str],
    ) -> float:
        """MRR: reciprocal rank of the first relevant document."""
        for i, r in enumerate(retrieved, 1):
            if r.get("event_id") in relevant_ids:
                return 1.0 / i
        return 0.0

    @staticmethod
    def average_precision(
        retrieved: List[Dict[str, Any]],
        relevant_ids: Set[str],
    ) -> float:
        """Average Precision (AP) for a single query."""
        if not relevant_ids:
            return 0.0
        score = 0.0
        relevant_count = 0
        for i, r in enumerate(retrieved, 1):
            if r.get("event_id") in relevant_ids:
                relevant_count += 1
                score += relevant_count / i
        return score / len(relevant_ids)

    @staticmethod
    def ndcg_at_k(
        retrieved: List[Dict[str, Any]],
        relevant_ids: Set[str],
        k: int = 10,
    ) -> float:
        """Normalized Discounted Cumulative Gain at K."""
        dcg = 0.0
        for i, r in enumerate(retrieved[:k], 1):
            rel = 1.0 if r.get("event_id") in relevant_ids else 0.0
            dcg += (2**rel - 1) / math.log2(i + 1)

        ideal_relevance = sorted(
            [1.0] * min(len(relevant_ids), k) + [0.0] * (k - min(len(relevant_ids), k)),
            reverse=True,
        )
        idcg = 0.0
        for i, rel in enumerate(ideal_relevance, 1):
            idcg += (2**rel - 1) / math.log2(i + 1)

        return dcg / idcg if idcg > 0 else 0.0

    @staticmethod
    def diversity_score(
        retrieved: List[Dict[str, Any]],
        top_k: int = 10,
    ) -> Dict[str, float]:
        """Measure diversity of retrieved results across event types, locations, sectors."""
        top = retrieved[:top_k]
        if not top:
            return {"event_type_diversity": 0.0, "location_diversity": 0.0, "sector_diversity": 0.0}

        event_types: Set[str] = set()
        locations: Set[str] = set()
        sectors: Set[str] = set()

        for r in top:
            meta = r.get("metadata", {})
            et = meta.get("event_type", "")
            loc = meta.get("location", "")
            sec = meta.get("sectors", "")

            if et:
                event_types.add(et)
            if loc:
                locations.add(loc)
            if sec:
                sectors.update(s.strip() for s in sec.split(",") if s.strip())

        return {
            "event_type_diversity": round(len(event_types) / len(top), 4),
            "location_diversity": round(len(locations) / len(top), 4),
            "sector_diversity": round(len(sectors) / max(len(top), 1), 4),
        }

    @staticmethod
    def evaluate_retrieval(
        retrieved: List[Dict[str, Any]],
        relevant_ids: Set[str],
        ks: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Run all evaluation metrics and return comprehensive results."""
        k_list = ks or [1, 3, 5, 10, 20]
        metrics: Dict[str, Any] = {
            "total_retrieved": len(retrieved),
            "total_relevant": len(relevant_ids),
            "mrr": round(RetrievalEvaluator.mean_reciprocal_rank(retrieved, relevant_ids), 4),
            "map": round(RetrievalEvaluator.average_precision(retrieved, relevant_ids), 4),
        }

        for k in k_list:
            if k > len(retrieved):
                continue
            metrics[f"p@{k}"] = round(
                RetrievalEvaluator.precision_at_k(retrieved, relevant_ids, k), 4
            )
            metrics[f"r@{k}"] = round(
                RetrievalEvaluator.recall_at_k(retrieved, relevant_ids, k), 4
            )
            metrics[f"f1@{k}"] = round(
                RetrievalEvaluator.f1_at_k(retrieved, relevant_ids, k), 4
            )
            metrics[f"ndcg@{k}"] = round(
                RetrievalEvaluator.ndcg_at_k(retrieved, relevant_ids, k), 4
            )

        metrics["diversity"] = RetrievalEvaluator.diversity_score(retrieved)
        return metrics


class RelevanceJudgment:
    """Build relevance judgments for evaluation from ground truth data."""

    def __init__(self) -> None:
        self._judgments: Dict[str, Set[str]] = {}

    def add_judgment(
        self,
        query_id: str,
        relevant_event_ids: List[str],
    ) -> None:
        self._judgments[query_id] = set(relevant_event_ids)

    def get_relevant(self, query_id: str) -> Set[str]:
        return self._judgments.get(query_id, set())

    def from_event_metadata(
        self,
        events: List[Dict[str, Any]],
        match_on: str = "event_type",
    ) -> Dict[str, Set[str]]:
        """Build relevance judgments automatically: events sharing a field are relevant."""
        groups: Dict[str, Set[str]] = {}
        for event in events:
            meta = event.get("metadata", {})
            key = meta.get(match_on, "unknown")
            eid = event.get("event_id", "")
            if eid:
                if key not in groups:
                    groups[key] = set()
                groups[key].add(eid)

        judgments: Dict[str, Set[str]] = {}
        for key, eids in groups.items():
            for eid in eids:
                if eid not in judgments:
                    judgments[eid] = set()
                judgments[eid] = judgments[eid] | (eids - {eid})

        return judgments


def evaluate_retrieval_quality(
    queries_results: Dict[str, List[Dict[str, Any]]],
    ground_truth: Dict[str, Set[str]],
) -> Dict[str, Any]:
    """Evaluate retrieval quality across multiple queries."""
    evaluator = RetrievalEvaluator()
    all_metrics: Dict[str, Any] = {}

    total_p_10 = 0.0
    total_r_10 = 0.0
    total_mrr = 0.0
    total_map = 0.0
    query_count = 0

    for query_id, results in queries_results.items():
        relevant = ground_truth.get(query_id, set())
        if not relevant:
            continue

        metrics = evaluator.evaluate_retrieval(results, relevant)
        all_metrics[query_id] = metrics
        total_p_10 += metrics.get("p@10", 0)
        total_r_10 += metrics.get("r@10", 0)
        total_mrr += metrics.get("mrr", 0)
        total_map += metrics.get("map", 0)
        query_count += 1

    if query_count > 0:
        summary = {
            "num_queries": query_count,
            "mean_p_10": round(total_p_10 / query_count, 4),
            "mean_r_10": round(total_r_10 / query_count, 4),
            "mean_mrr": round(total_mrr / query_count, 4),
            "mean_map": round(total_map / query_count, 4),
        }
    else:
        summary = {
            "num_queries": 0,
            "mean_p_10": 0.0,
            "mean_r_10": 0.0,
            "mean_mrr": 0.0,
            "mean_map": 0.0,
        }

    return {"summary": summary, "per_query": all_metrics}
