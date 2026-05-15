from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.config import settings
from app.logging_config import get_logger
from app.services.chroma.client import ChromaClient
from app.services.chroma.embeddings import EmbeddingService
from app.services.rag.prompts import RAG_PROMPT_TEMPLATES
from app.services.rag.retriever import Retriever

logger = get_logger(__name__)


class RAGEngine:
    """Retrieval-Augmented Generation engine for geopolitical financial intelligence."""

    def __init__(
        self,
        chroma_client: Optional[ChromaClient] = None,
        embedding_service: Optional[EmbeddingService] = None,
        retriever: Optional[Retriever] = None,
    ) -> None:
        self.chroma = chroma_client or ChromaClient()
        self.embeddings = embedding_service or EmbeddingService()
        self.retriever = retriever or Retriever(self.chroma)

    async def query(
        self,
        query_text: str,
        collections: Optional[List[str]] = None,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        prompt_template: str = "default",
    ) -> Dict[str, Any]:
        import time
        start = time.perf_counter()

        retrieved = await self.retriever.retrieve(
            query=query_text,
            collections=collections,
            top_k=top_k,
            filters=filters,
        )

        context_str = self.retriever.format_context(retrieved)
        template = RAG_PROMPT_TEMPLATES.get(prompt_template, RAG_PROMPT_TEMPLATES["default"])

        full_prompt = template.format(
            context=context_str,
            query=query_text,
        )

        try:
            from app.utils.llm_client import create_llm_client
            client = create_llm_client()
            response = await client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": "You are a geopolitical financial intelligence assistant. Use the provided context to answer accurately."},
                    {"role": "user", "content": full_prompt},
                ],
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=settings.OPENAI_MAX_TOKENS,
            )
            answer = response.choices[0].message.content or ""
        except Exception as e:
            logger.warning("LLM call failed in RAG engine: %s", e)
            if retrieved:
                top = retrieved[0]
                answer = f"Found {len(retrieved)} relevant results. Top match: {top.get('content', '')[:200]}..."
            else:
                answer = "No relevant data found in the knowledge base. Try a different query or index some documents first."

        elapsed = (time.perf_counter() - start) * 1000

        return {
            "query": query_text,
            "answer": answer,
            "results": retrieved,
            "total_results": len(retrieved),
            "processing_time_ms": round(elapsed, 2),
            "model_used": settings.llm_model,
        }

    async def hybrid_query(
        self,
        query_text: str,
        collections: Optional[List[str]] = None,
        top_k: int = 10,
    ) -> Dict[str, Any]:
        return await self.query(
            query_text=query_text,
            collections=collections,
            top_k=top_k,
            prompt_template="analysis",
        )
