from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.logging_config import get_logger
from app.models.geopol_event import GeoPolEvent
from app.models.sentiment import SentimentData
from app.services.chroma.client import ChromaClient
from app.services.chroma.embeddings import EmbeddingService

logger = get_logger(__name__)

class GeoPolStorage:
    """Service for storing Geopolitical events in ChromaDB and Postgres."""
    
    def __init__(self, chroma: Optional[ChromaClient] = None, embeddings: Optional[EmbeddingService] = None):
        self.chroma = chroma or ChromaClient()
        self.embeddings = embeddings or EmbeddingService()
        self.collection_name = "geopol_events"

    async def save_events(self, events: List[GeoPolEvent]) -> int:
        """Batch save events to ChromaDB."""
        if not events:
            return 0
            
        ids = []
        documents = []
        metadatas = []
        embeddings = []
        
        for event in events:
            event_id = event.id or str(uuid4())
            ids.append(event_id)
            
            # Create a rich document for embedding
            doc = f"{event.title}. {event.description}. Type: {event.event_type}. Location: {event.location}."
            documents.append(doc)
            
            # Create metadata
            meta = {
                "source": event.source,
                "event_date": event.event_date.isoformat(),
                "location": event.location,
                "event_type": event.event_type,
                "severity": event.severity,
                "actors": ",".join(event.actors) if event.actors else "",
                "sectors": ",".join(event.affected_sectors) if event.affected_sectors else "",
                "source_url": event.source_url,
                "ingested_at": datetime.utcnow().isoformat()
            }
            metadatas.append(meta)
            
        # Compute embeddings in batch
        try:
            embeddings = await self.embeddings.embed_texts(documents)
            
            await self.chroma.add_documents(
                collection_name=self.collection_name,
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings
            )
            logger.info("Successfully stored %d events in ChromaDB", len(events))
            return len(events)
        except Exception as e:
            logger.error("Failed to store events in ChromaDB: %s", e)
            return 0

    async def save_sentiment(self, data: List[SentimentData]) -> int:
        """Batch save sentiment data to ChromaDB."""
        if not data:
            return 0
            
        ids = [d.post_id for d in data]
        documents = [f"{d.title} {d.text}" for d in data]
        metadatas = []
        
        for d in data:
            metadatas.append({
                "source": d.source,
                "platform": d.platform,
                "subreddit": d.subreddit,
                "sentiment_score": d.sentiment_score,
                "sentiment_label": d.sentiment_label,
                "confidence": d.confidence,
                "tickers": ",".join(d.tickers_mentioned),
                "created_at": d.created_utc.isoformat(),
                "ingested_at": datetime.utcnow().isoformat()
            })
            
        try:
            embeddings = await self.embeddings.embed_texts(documents)
            await self.chroma.add_documents(
                collection_name="sentiment_data",
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings
            )
            return len(data)
        except Exception as e:
            logger.error("Failed to store sentiment in ChromaDB: %s", e)
            return 0

    async def save_market_data(self, ticker: str, data: List[Dict[str, Any]]) -> int:
        """Batch save market data points to ChromaDB."""
        if not data:
            return 0
            
        ids = [f"{ticker}_{d.get('date') or d.get('timestamp')}" for d in data]
        documents = [f"Market data for {ticker} on {d.get('date') or d.get('timestamp')}. Close: {d.get('close')}." for d in data]
        metadatas = []
        
        for d in data:
            metadatas.append({
                "ticker": ticker,
                "date": str(d.get("date") or d.get("timestamp")),
                "open": float(d.get("open", 0)),
                "high": float(d.get("high", 0)),
                "low": float(d.get("low", 0)),
                "close": float(d.get("close", 0)),
                "volume": int(d.get("volume", 0)),
                "ingested_at": datetime.utcnow().isoformat()
            })
            
        try:
            embeddings = await self.embeddings.embed_texts(documents)
            await self.chroma.add_documents(
                collection_name="market_data",
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings
            )
            return len(data)
        except Exception as e:
            logger.error("Failed to store market data in ChromaDB: %s", e)
            return 0

geopol_storage = GeoPolStorage()
