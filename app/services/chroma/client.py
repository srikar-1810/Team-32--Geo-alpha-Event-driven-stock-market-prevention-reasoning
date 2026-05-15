from __future__ import annotations

from typing import Any, Dict, List, Optional

import chromadb
from chromadb.api.types import EmbeddingFunction

from app.config import settings
from app.logging_config import get_logger
from app.services.base import BaseService

logger = get_logger(__name__)


class ChromaClient(BaseService):
    """Async-compatible ChromaDB vector store client."""

    def __init__(self, embedding_function: Optional[EmbeddingFunction] = None) -> None:
        super().__init__("chroma")
        self._client: Optional[chromadb.AsyncHttpClient] = None
        self._embedding_function = embedding_function

    async def _get_client(self) -> chromadb.AsyncHttpClient:
        if self._client is None:
            self._client = await chromadb.AsyncHttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT,
                settings=chromadb.Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )
        return self._client

    async def get_or_create_collection(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> chromadb.AsyncCollection:
        client = await self._get_client()
        try:
            collection = await client.get_collection(name)
        except Exception:
            collection = await client.create_collection(
                name=name,
                metadata=metadata or {"hnsw:space": "cosine"},
                embedding_function=self._embedding_function,
            )
        return collection

    async def add_documents(
        self,
        collection_name: str,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        embeddings: Optional[List[List[float]]] = None,
    ) -> bool:
        collection = await self.get_or_create_collection(collection_name)
        await collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        return True

    async def query(
        self,
        collection_name: str,
        query_texts: Optional[List[str]] = None,
        query_embeddings: Optional[List[List[float]]] = None,
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
        include: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        collection = await self.get_or_create_collection(collection_name)
        results = await collection.query(
            query_texts=query_texts,
            query_embeddings=query_embeddings,
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=include or ["documents", "metadatas", "distances"],
        )
        return results

    async def delete_collection(self, name: str) -> bool:
        client = await self._get_client()
        await client.delete_collection(name)
        return True

    async def list_collections(self) -> List[Dict[str, Any]]:
        client = await self._get_client()
        collections = await client.list_collections()
        result = []
        for coll in collections:
            result.append({
                "name": coll.name,
                "metadata": coll.metadata,
            })
        return result

    async def count(self, collection_name: str) -> int:
        collection = await self.get_or_create_collection(collection_name)
        return await collection.count()

    async def reset(self) -> None:
        client = await self._get_client()
        await client.reset()
        logger.warning("ChromaDB has been reset.")

    async def close(self) -> None:
        if self._client:
            await self._client.close()
