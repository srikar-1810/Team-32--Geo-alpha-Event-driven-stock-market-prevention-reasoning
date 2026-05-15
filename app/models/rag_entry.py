from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.models.base import Entity


class RAGDocument(Entity):
    collection: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    chunk_index: int = 0
    parent_document_id: Optional[str] = None
    embedding: Optional[List[float]] = None
    embedding_model: str = ""


class RAGQueryRecord(Entity):
    model_config = {"protected_namespaces": ()}
    query: str
    collection: str
    top_k: int
    results_count: int
    processing_time_ms: float
    model_used: str
    filters: Optional[Dict[str, Any]] = None
