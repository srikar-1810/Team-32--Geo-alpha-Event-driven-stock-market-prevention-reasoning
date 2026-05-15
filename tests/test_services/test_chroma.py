from __future__ import annotations

import pytest

from app.services.chroma.collections import CollectionManager
from app.services.chroma.embeddings import EmbeddingService


class TestEmbeddingService:
    @pytest.mark.asyncio
    async def test_get_dimension(self):
        svc = EmbeddingService("all-MiniLM-L6-v2")
        assert svc.get_dimension() == 384

    @pytest.mark.asyncio
    async def test_embed_text_returns_list(self):
        svc = EmbeddingService()
        result = await svc.embed_text("test text")
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_embed_texts_returns_list_of_lists(self):
        svc = EmbeddingService()
        results = await svc.embed_texts(["text one", "text two"])
        assert isinstance(results, list)
