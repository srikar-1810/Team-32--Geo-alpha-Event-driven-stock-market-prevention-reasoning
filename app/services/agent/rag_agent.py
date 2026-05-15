from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.services.agent.base import BaseAgent
from app.services.chroma.client import ChromaClient
from app.services.chroma.embeddings import EmbeddingService


class RAGRetrievalAgent(BaseAgent):
    """Retrieves relevant historical context using RAG."""

    def __init__(
        self,
        chroma_client: Optional[ChromaClient] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ) -> None:
        super().__init__(
            agent_id="rag-agent",
            name="RAG Retrieval Agent",
        )
        self.chroma = chroma_client or ChromaClient()
        self.embeddings = embedding_service or EmbeddingService()

    async def run(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        query = input_data.get("query", "")
        collections = input_data.get(
            "collections",
            ["geopol_events", "sentiment_data", "market_data", "reports"],
        )
        top_k = input_data.get("top_k", 5)

        all_results = []
        for collection in collections:
            try:
                results = await self.chroma.query(
                    collection_name=collection,
                    query_texts=[query],
                    n_results=top_k,
                )
                doc_ids = results.get("ids", [[]])[0]
                documents = results.get("documents", [[]])[0]
                distances = results.get("distances", [[]])[0]
                metadatas = results.get("metadatas", [[]])[0]

                for i, doc_id in enumerate(doc_ids):
                    all_results.append({
                        "id": doc_id,
                        "content": documents[i] if i < len(documents) else "",
                        "score": 1.0 - distances[i] if i < len(distances) else 0.0,
                        "metadata": metadatas[i] if i < len(metadatas) else {},
                        "collection": collection,
                    })
            except Exception as e:
                self.logger.warning("RAG query failed for %s: %s", collection, e)

        all_results.sort(key=lambda x: x["score"], reverse=True)

        context_str = self._format_context(all_results)
        analysis_prompt = (
            f"Using the following historical context retrieved from the knowledge base, "
            f"answer the query.\n\n"
            f"Query: {query}\n\n"
            f"Retrieved Context:\n{context_str}\n\n"
            f"Provide a synthesis of relevant information and how it applies."
        )

        llm_output = await self._call_llm(
            system_prompt="You are a knowledge retrieval specialist synthesizing information from vector databases.",
            user_prompt=analysis_prompt,
        )

        self._add_to_memory("user", str(input_data))
        self._add_to_memory("assistant", llm_output)

        return {
            "agent": self.agent_id,
            "status": "completed",
            "query": query,
            "results_count": len(all_results),
            "results": all_results[:top_k],
            "synthesis": llm_output,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _format_context(self, results: List[Dict[str, Any]]) -> str:
        lines = []
        for i, r in enumerate(results[:10], 1):
            lines.append(
                f"[{i}] (score={r['score']:.3f}, collection={r['collection']})\n"
                f"{r['content'][:300]}...\n"
            )
        return "\n".join(lines)
