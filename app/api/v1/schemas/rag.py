from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    collection: str = Field(default="geopol_events")
    top_k: int = Field(default=5, ge=1, le=50)
    filters: Optional[Dict[str, Any]] = None
    include_metadata: bool = True


class RAGResultItem(BaseModel):
    id: str
    score: float
    content: str
    metadata: Dict[str, Any]
    collection: str


class RAGQueryResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    query: str
    answer: str = ""
    results: List[RAGResultItem]
    total_results: int
    processing_time_ms: float
    model_used: str


class RAGIndexDocumentRequest(BaseModel):
    collection: str
    content: str = Field(..., min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    chunk_size: int = Field(default=512, ge=128, le=2048)
    chunk_overlap: int = Field(default=64, ge=0, le=512)


class RAGIndexDocumentResponse(BaseModel):
    document_id: str
    collection: str
    chunk_count: int
    indexed_at: datetime


class RAGCollectionStats(BaseModel):
    name: str
    document_count: int
    embedding_dimension: int
    created_at: str


# ── Historical RAG Schemas ────────────────────────────────────

class HistoricalRAGSimilarityResult(BaseModel):
    event_id: str
    event_title: str = ""
    event_type: str = ""
    location: str = ""
    event_date: str = ""
    similarity: float = 0.0
    distance: float = 0.0
    severity: float = 0.0
    data_quality: str = "medium"
    sectors: str = ""
    bullish_tickers: str = ""
    bearish_tickers: str = ""
    impact_summary: str = ""
    confidence: Dict[str, Any] = Field(default_factory=dict)


class HistoricalRAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000)
    top_k: int = Field(default=10, ge=1, le=100)
    min_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    filters: Optional[Dict[str, Any]] = None
    include_confidence: bool = True
    include_market_reactions: bool = True


class HistoricalRAGEventQueryRequest(BaseModel):
    event_id: str = Field(..., description="ID of the event to find analogues for")
    top_k: int = Field(default=10, ge=1, le=50)
    exclude_self: bool = True


class HistoricalRAGFilterQueryRequest(BaseModel):
    top_k: int = Field(default=20, ge=1, le=100)
    event_type: Optional[str] = None
    location: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    sector: Optional[str] = None
    min_severity: Optional[float] = None


class HistoricalRAGMarketReactions(BaseModel):
    avg_volatility_change_pct: float = 0.0
    avg_market_return_5d: float = 0.0
    avg_market_return_30d: float = 0.0
    sectors_by_impact: List[Dict[str, Any]] = Field(default_factory=list)
    most_common_bullish: List[Dict[str, Any]] = Field(default_factory=list)
    most_common_bearish: List[Dict[str, Any]] = Field(default_factory=list)
    total_events_analyzed: int = 0


class HistoricalRAGQueryResponse(BaseModel):
    query: str
    total_results: int
    processing_time_ms: float
    results: List[HistoricalRAGSimilarityResult] = Field(default_factory=list)
    market_reactions: Optional[HistoricalRAGMarketReactions] = None


class HistoricalRAGIndexResponse(BaseModel):
    success: int
    total: int
    collection: str
    indexed_at: str


class HistoricalRAGCollectionStatsResponse(BaseModel):
    collection: str
    document_count: int
    embedding_dimension: int
    cache_stats: Dict[str, Any] = Field(default_factory=dict)


class HistoricalRAGEvaluationRequest(BaseModel):
    query: str
    relevant_event_ids: List[str] = Field(..., min_length=1)


class HistoricalRAGEvaluationResponse(BaseModel):
    query: str
    retrieved_count: int
    relevant_count: int
    metrics: Dict[str, Any] = Field(default_factory=dict)
