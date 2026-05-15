from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.config import settings
from app.logging_config import get_logger
from app.services.chroma.client import ChromaClient

logger = get_logger(__name__)


class Retriever:
    """Document retriever that queries ChromaDB collections."""

    DEFAULT_COLLECTIONS = [
        settings.CHROMA_COLLECTION_EVENTS,
        settings.CHROMA_COLLECTION_SENTIMENT,
        settings.CHROMA_COLLECTION_MARKETS,
        settings.CHROMA_COLLECTION_REPORTS,
    ]

    def __init__(self, chroma_client: ChromaClient) -> None:
        self.chroma = chroma_client

    async def retrieve(
        self,
        query: str,
        collections: Optional[List[str]] = None,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        targets = collections or self.DEFAULT_COLLECTIONS
        all_results = []

        for collection in targets:
            try:
                results = await self.chroma.query(
                    collection_name=collection,
                    query_texts=[query],
                    n_results=top_k,
                    where=filters,
                )
                doc_ids = results.get("ids", [[]])[0]
                documents = results.get("documents", [[]])[0]
                distances = results.get("distances", [[]])[0]
                metadatas = results.get("metadatas", [[]])[0]

                for i in range(len(doc_ids)):
                    all_results.append({
                        "id": doc_ids[i],
                        "content": documents[i] if i < len(documents) else "",
                        "score": 1.0 - distances[i] if i < len(distances) else 0.0,
                        "metadata": metadatas[i] if i < len(metadatas) else {},
                        "collection": collection,
                    })
            except Exception as e:
                logger.debug("Retrieval failed for collection %s: %s", collection, e)

        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:top_k]

    def format_context(self, results: List[Dict[str, Any]], max_chars: int = 4000) -> str:
        lines = []
        total = 0
        for i, r in enumerate(results, 1):
            content = r.get("content", "")[:500]
            meta = r.get("metadata", {})
            source = meta.get("source", r.get("collection", "unknown"))
            date_str = meta.get("date", meta.get("event_date", ""))
            score = r.get("score", 0.0)

            entry = (
                f"[{i}] Source: {source} | Date: {date_str} | Score: {score:.3f}\n"
                f"{content}\n"
            )
            if total + len(entry) > max_chars:
                break
            lines.append(entry)
            total += len(entry)

        return "\n".join(lines) if lines else "No relevant documents found."
