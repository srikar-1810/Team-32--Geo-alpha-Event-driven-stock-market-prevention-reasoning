from __future__ import annotations

from typing import List, Optional

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """Generates embeddings using sentence-transformers or OpenAI."""

    def __init__(self, model_name: Optional[str] = None) -> None:
        self.model_name = model_name or settings.CHROMA_EMBEDDING_MODEL
        self._model = None
        self._openai_client = None

    async def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                logger.info("Loaded sentence-transformer model: %s", self.model_name)
            except Exception as e:
                logger.warning("Failed to load sentence-transformers: %s", e)
                self._model = None

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        await self._load_model()
        if self._model:
            embeddings = self._model.encode(texts, show_progress_bar=False)
            return embeddings.tolist()
        try:
            return await self._embed_openai(texts)
        except Exception as e:
            logger.warning("OpenAI embedding failed: %s. Using random embeddings.", e)
            import numpy as np
            return np.random.rand(len(texts), 384).tolist()

    async def embed_text(self, text: str) -> List[float]:
        result = await self.embed_texts([text])
        return result[0] if result else []

    async def _embed_openai(self, texts: List[str]) -> List[List[float]]:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def get_dimension(self) -> int:
        model_dimensions = {
            "all-MiniLM-L6-v2": 384,
            "all-mpnet-base-v2": 768,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
        }
        return model_dimensions.get(self.model_name, 384)
