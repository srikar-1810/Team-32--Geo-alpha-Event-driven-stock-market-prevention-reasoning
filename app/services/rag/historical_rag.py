from __future__ import annotations

import time
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from app.config import settings
from app.logging_config import get_logger
from app.services.chroma.client import ChromaClient
from app.services.chroma.embeddings import EmbeddingService
from app.services.historical.models import (
    DataQuality,
    HistoricalMarketImpact,
    ImpactDirection,
)
from app.services.rag.embedding_cache import EmbeddingCache

logger = get_logger(__name__)

HISTORICAL_COLLECTION = "historical_events"


class HistoricalRAGService:
    """RAG service for historical geopolitical market events with ChromaDB."""

    def __init__(
        self,
        chroma: Optional[ChromaClient] = None,
        embeddings: Optional[EmbeddingService] = None,
        cache: Optional[EmbeddingCache] = None,
    ) -> None:
        self.chroma = chroma or ChromaClient()
        self.embeddings = embeddings or EmbeddingService()
        self.cache = cache or EmbeddingCache(
            capacity=settings.CHROMA_EMBEDDING_CACHE_SIZE,
        )

    # ── Document Building ──────────────────────────────────────────

    def build_event_document(self, event: HistoricalMarketImpact) -> str:
        """Build a rich text document for embedding that captures all facets."""
        parts: List[str] = []
        parts.append(f"Event: {event.event_title}")
        parts.append(f"Description: {event.event_description}")
        parts.append(f"Type: {event.event_type}")
        parts.append(f"Location: {event.location}")
        parts.append(f"Countries: {', '.join(event.countries)}")
        parts.append(f"Actors: {', '.join(event.actors)}")
        parts.append(f"Date: {event.event_date.strftime('%Y-%m-%d')}")
        parts.append(f"Severity: {event.severity:.2f}")
        parts.append(f"Confidence: {event.confidence:.2f}")

        if event.sectors_impacted:
            parts.append("Sector Impacts:")
            for s in event.sectors_impacted:
                parts.append(
                    f"  {s.sector_name} ({s.etf_ticker}): "
                    f"1d={s.return_1d:+.2f}% 5d={s.return_5d:+.2f}% "
                    f"10d={s.return_10d:+.2f}% 30d={s.return_30d:+.2f}% "
                    f"dir={s.direction.value} vol={s.volatility_impact:+.2f}%"
                )
                if s.stocks:
                    top = sorted(s.stocks, key=lambda x: abs(x.return_5d), reverse=True)[:3]
                    for st in top:
                        parts.append(
                            f"    {st.ticker}: 5d={st.return_5d:+.2f}% dir={st.direction.value}"
                        )

        if event.top_bullish_stocks:
            parts.append("Bullish:")
            for s in event.top_bullish_stocks[:5]:
                parts.append(f"  {s['ticker']}: {s.get('return_5d', 0):+.2f}%")

        if event.top_bearish_stocks:
            parts.append("Bearish:")
            for s in event.top_bearish_stocks[:5]:
                parts.append(f"  {s['ticker']}: {s.get('return_5d', 0):+.2f}%")

        parts.append(f"Volatility change: {event.volatility_change_pct:+.2f}%")
        parts.append(f"Market 5d return: {event.overall_market_return_5d:+.2f}%")
        parts.append(f"Market 30d return: {event.overall_market_return_30d:+.2f}%")
        parts.append(f"Impact summary: {event.impact_summary}")
        parts.append(f"Historical analogues: {'; '.join(event.historical_analogues)}")
        parts.append(f"Source: {event.source}")
        parts.append(f"Data quality: {event.data_quality.value}")

        return "\n".join(parts)

    def _build_metadata(self, event: HistoricalMarketImpact) -> Dict[str, Any]:
        return {
            "event_id": event.event_id,
            "event_title": event.event_title,
            "event_type": event.event_type,
            "location": event.location,
            "countries": ",".join(event.countries) if event.countries else "",
            "event_date": event.event_date.isoformat() if event.event_date else "",
            "goldstein_scale": event.goldstein_scale,
            "num_mentions": event.num_mentions,
            "severity": event.severity,
            "confidence": event.confidence,
            "data_quality": event.data_quality.value,
            "source": event.source,
            "dataset_version": event.dataset_version,
            "volatility_change_pct": event.volatility_change_pct,
            "overall_market_return_5d": event.overall_market_return_5d,
            "overall_market_return_30d": event.overall_market_return_30d,
            "sectors": ",".join(
                s.sector_name for s in event.sectors_impacted
            ) if event.sectors_impacted else "",
            "sector_directions": ",".join(
                s.direction.value for s in event.sectors_impacted
            ) if event.sectors_impacted else "",
            "bullish_tickers": ",".join(
                s["ticker"] for s in (event.top_bullish_stocks or [])
            ),
            "bearish_tickers": ",".join(
                s["ticker"] for s in (event.top_bearish_stocks or [])
            ),
            "impact_summary": event.impact_summary,
            "historical_analogues": ";".join(event.historical_analogues),
            "tone_score": event.tone.tone_score if event.tone else 0.0,
            "tone_polarity": event.tone.polarity if event.tone else 0.0,
        }

    # ── Indexing ────────────────────────────────────────────────────

    async def index_event(
        self,
        event: HistoricalMarketImpact,
        collection: str = HISTORICAL_COLLECTION,
    ) -> bool:
        """Embed and store a single historical event in ChromaDB."""
        document = self.build_event_document(event)
        metadata = self._build_metadata(event)

        cached = self.cache.get(document)
        if cached is not None:
            embedding = cached
        else:
            embedding = await self.embeddings.embed_text(document)
            self.cache.put(document, embedding)

        event_id = event.event_id or str(uuid4())
        try:
            await self.chroma.add_documents(
                collection_name=collection,
                ids=[event_id],
                documents=[document],
                metadatas=[metadata],
                embeddings=[embedding],
            )
            logger.debug("Indexed event %s in collection '%s'", event_id[:8], collection)
            return True
        except Exception as e:
            logger.error("Failed to index event %s: %s", event_id[:8], e)
            return False

    async def index_events_batch(
        self,
        events: List[HistoricalMarketImpact],
        collection: str = HISTORICAL_COLLECTION,
        batch_size: int = 50,
    ) -> Tuple[int, int]:
        """Batch index multiple events into ChromaDB. Returns (success, total)."""
        await self.cache.load_from_disk()

        success = 0
        total = len(events)

        for i in range(0, total, batch_size):
            batch = events[i:i + batch_size]
            documents = [self.build_event_document(e) for e in batch]
            metadatas = [self._build_metadata(e) for e in batch]
            ids = [e.event_id or str(uuid4()) for e in batch]

            embeddings_to_compute = []
            indices_to_compute = []
            for j, doc in enumerate(documents):
                cached = self.cache.get(doc)
                if cached is not None:
                    embeddings_to_compute.append(cached)
                else:
                    embeddings_to_compute.append(None)
                    indices_to_compute.append(j)

            if indices_to_compute:
                texts_to_embed = [documents[j] for j in indices_to_compute]
                computed = await self.embeddings.embed_texts(texts_to_embed)
                for idx, emb in zip(indices_to_compute, computed):
                    embeddings_to_compute[idx] = emb
                    self.cache.put(documents[idx], emb)

            batch_embeddings = embeddings_to_compute

            try:
                await self.chroma.add_documents(
                    collection_name=collection,
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                    embeddings=batch_embeddings,
                )
                success += len(batch)
                logger.debug("Indexed batch %d-%d of %d", i, i + len(batch), total)
            except Exception as e:
                logger.error("Batch index failed at %d: %s", i, e)

        await self.cache.save_to_disk()
        logger.info(
            "Batch indexing complete: %d/%d events indexed in '%s'",
            success, total, collection,
        )
        return success, total

    async def reindex_collection(
        self,
        events: List[HistoricalMarketImpact],
        collection: str = HISTORICAL_COLLECTION,
    ) -> Tuple[int, int]:
        """Drop and rebuild an entire collection from scratch."""
        try:
            await self.chroma.delete_collection(collection)
            logger.info("Deleted and will rebuild collection '%s'", collection)
        except Exception:
            pass
        return await self.index_events_batch(events, collection)

    # ── Retrieval ──────────────────────────────────────────────────

    async def retrieve_similar(
        self,
        query_text: str,
        collection: str = HISTORICAL_COLLECTION,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        min_similarity: float = 0.0,
        include_embeddings: bool = False,
    ) -> List[Dict[str, Any]]:
        """Retrieve historical events similar to a query text."""
        query_embedding = await self.embeddings.embed_text(query_text)

        include = ["documents", "metadatas", "distances"]
        if include_embeddings:
            include.append("embeddings")

        try:
            results = await self.chroma.query(
                collection_name=collection,
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filters,
                include=include,
            )
        except Exception as e:
            logger.error("Retrieval query failed: %s", e)
            return []

        doc_ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        retrieved = []
        for i in range(len(doc_ids)):
            score = 1.0 - distances[i] if i < len(distances) else 0.0
            if score < min_similarity:
                continue

            item: Dict[str, Any] = {
                "event_id": doc_ids[i],
                "content": documents[i] if i < len(documents) else "",
                "similarity": round(score, 4),
                "distance": round(distances[i], 4) if i < len(distances) else 1.0,
                "metadata": metadatas[i] if i < len(metadatas) else {},
            }
            retrieved.append(item)

        retrieved.sort(key=lambda x: x["similarity"], reverse=True)
        return retrieved

    async def retrieve_by_event(
        self,
        event: HistoricalMarketImpact,
        collection: str = HISTORICAL_COLLECTION,
        top_k: int = 10,
        exclude_self: bool = True,
    ) -> List[Dict[str, Any]]:
        """Retrieve historical events similar to a given event object."""
        document = self.build_event_document(event)
        results = await self.retrieve_similar(
            query_text=document,
            collection=collection,
            top_k=top_k + 1 if exclude_self else top_k,
        )
        if exclude_self and results:
            results = [r for r in results if r["event_id"] != event.event_id]
        return results[:top_k]

    async def retrieve_by_filters(
        self,
        collection: str = HISTORICAL_COLLECTION,
        top_k: int = 50,
        event_type: Optional[str] = None,
        location: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sector: Optional[str] = None,
        min_severity: Optional[float] = None,
        min_similarity: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Retrieve events by structured filters."""
        where_clause: Dict[str, Any] = {}

        if event_type:
            where_clause["event_type"] = event_type
        if location:
            where_clause["location"] = location
        if sector:
            where_clause["sectors"] = sector

        filters = None
        if where_clause:
            filters = where_clause

        if min_severity is not None:
            base_filters = filters or {}
            base_filters["severity"] = {"$gte": min_severity}
            filters = base_filters

        try:
            results = await self.chroma.query(
                collection_name=collection,
                query_texts=[""],
                n_results=top_k,
                where=filters,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.error("Filtered retrieval failed: %s", e)
            return []

        doc_ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        retrieved = []
        for i in range(len(doc_ids)):
            score = 1.0 - distances[i] if i < len(distances) else 0.0
            if score < min_similarity:
                continue

            meta = metadatas[i] if i < len(metadatas) else {}
            if date_from:
                ed = meta.get("event_date", "")
                if ed and ed < date_from:
                    continue
            if date_to:
                ed = meta.get("event_date", "")
                if ed and ed > date_to:
                    continue

            retrieved.append({
                "event_id": doc_ids[i],
                "content": documents[i] if i < len(documents) else "",
                "similarity": round(score, 4),
                "metadata": meta,
            })

        return retrieved

    # ── Confidence Scoring ─────────────────────────────────────────

    def compute_confidence(
        self,
        similarity: float,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Compute a detailed confidence score for a retrieval result."""
        evidence: List[str] = []
        signals: List[float] = []

        signals.append(similarity)
        if similarity > 0.8:
            evidence.append("Very high semantic similarity")
        elif similarity > 0.6:
            evidence.append("Strong semantic similarity")
        elif similarity > 0.4:
            evidence.append("Moderate semantic similarity")

        quality = metadata.get("data_quality", "medium")
        quality_scores = {"high": 1.0, "medium": 0.6, "low": 0.3}
        signals.append(quality_scores.get(quality, 0.5))
        evidence.append(f"Data quality: {quality}")

        severity = metadata.get("severity", 0)
        severity_score = min(1.0, severity / 10.0)
        signals.append(severity_score)
        if severity > 7:
            evidence.append("High severity event")
        elif severity > 3:
            evidence.append("Moderate severity event")

        tone_polarity = metadata.get("tone_polarity", 0)
        tone_conf = abs(tone_polarity)
        signals.append(tone_conf)
        if tone_conf > 0.5:
            evidence.append("Strong tonal signal")

        num_mentions = metadata.get("num_mentions", 0)
        mention_score = min(1.0, num_mentions / 100.0)
        signals.append(mention_score)
        if num_mentions > 50:
            evidence.append("High media coverage")
        elif num_mentions > 10:
            evidence.append("Moderate media coverage")

        has_market_data = bool(metadata.get("sectors", ""))
        signals.append(1.0 if has_market_data else 0.3)
        if has_market_data:
            evidence.append("Market impact data available")

        overall = sum(signals) / len(signals) if signals else 0.0
        overall = round(min(1.0, max(0.0, overall)), 4)

        if overall >= 0.7:
            level = "high"
        elif overall >= 0.4:
            level = "medium"
        else:
            level = "low"

        return {
            "score": overall,
            "level": level,
            "evidence": evidence[:6],
            "signals": {
                "similarity": round(similarity, 4),
                "quality": quality,
                "severity": severity,
                "tone_polarity": tone_polarity,
                "num_mentions": num_mentions,
                "has_market_data": has_market_data,
            },
        }

    # ── Context Building ───────────────────────────────────────────

    def build_llm_context(
        self,
        results: List[Dict[str, Any]],
        max_chars: int = 8000,
    ) -> str:
        """Build a formatted context string for LLM prompts."""
        lines: List[str] = []
        total_chars = 0

        lines.append("=== SIMILAR HISTORICAL GEOPOLITICAL EVENTS ===")
        lines.append("")

        for i, r in enumerate(results, 1):
            meta = r.get("metadata", {})
            content = r.get("content", "")
            sim = r.get("similarity", 0.0)

            event_title = meta.get("event_title", "Unknown")
            event_type = meta.get("event_type", "Unknown")
            event_date = meta.get("event_date", "")
            location = meta.get("location", "")
            severity = meta.get("severity", 0)
            quality = meta.get("data_quality", "medium")
            sectors = meta.get("sectors", "")
            bullish = meta.get("bullish_tickers", "")
            bearish = meta.get("bearish_tickers", "")

            entry_lines: List[str] = []
            entry_lines.append(f"[{i}] {event_title}")
            entry_lines.append(f"    Type: {event_type} | Date: {event_date} | Location: {location}")
            entry_lines.append(f"    Severity: {severity} | Quality: {quality} | Similarity: {sim:.3f}")

            if sectors:
                entry_lines.append(f"    Impacted sectors: {sectors}")
            if bullish:
                entry_lines.append(f"    Bullish tickers: {bullish}")
            if bearish:
                entry_lines.append(f"    Bearish tickers: {bearish}")

            impact_summary = meta.get("impact_summary", "")
            if impact_summary:
                preview = impact_summary[:200].replace("\n", " | ")
                entry_lines.append(f"    Summary: {preview}")

            entry_lines.append("")

            entry_text = "\n".join(entry_lines)
            if total_chars + len(entry_text) > max_chars:
                lines.append(f"... and {len(results) - i + 1} more similar events")
                break

            lines.append(entry_text)
            total_chars += len(entry_text)

        return "\n".join(lines)

    # ── Market Reaction Extraction ─────────────────────────────────

    def extract_market_reactions(
        self,
        results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Extract aggregated market reactions from similar events."""
        all_sector_impacts: Dict[str, List[float]] = {}
        all_bullish: List[str] = []
        all_bearish: List[str] = []
        all_vol_changes: List[float] = []
        all_market_returns_5d: List[float] = []
        all_market_returns_30d: List[float] = []

        for r in results:
            meta = r.get("metadata", {})
            sim = r.get("similarity", 0.0)

            sectors_str = meta.get("sectors", "")
            if sectors_str:
                for s_name in sectors_str.split(","):
                    s_name = s_name.strip()
                    if s_name not in all_sector_impacts:
                        all_sector_impacts[s_name] = []
                    all_sector_impacts[s_name].append(sim)

            bullish_str = meta.get("bullish_tickers", "")
            if bullish_str:
                all_bullish.extend(
                    t.strip() for t in bullish_str.split(",") if t.strip()
                )

            bearish_str = meta.get("bearish_tickers", "")
            if bearish_str:
                all_bearish.extend(
                    t.strip() for t in bearish_str.split(",") if t.strip()
                )

            vol = meta.get("volatility_change_pct", 0)
            if vol:
                all_vol_changes.append(vol)

            mr5 = meta.get("overall_market_return_5d", 0)
            if mr5:
                all_market_returns_5d.append(mr5)

            mr30 = meta.get("overall_market_return_30d", 0)
            if mr30:
                all_market_returns_30d.append(mr30)

        from collections import Counter

        bullish_counts = Counter(all_bullish)
        bearish_counts = Counter(all_bearish)

        most_common_bullish = bullish_counts.most_common(10)
        most_common_bearish = bearish_counts.most_common(10)

        avg_vol = (
            sum(all_vol_changes) / len(all_vol_changes) if all_vol_changes else 0.0
        )
        avg_mr5 = (
            sum(all_market_returns_5d) / len(all_market_returns_5d)
            if all_market_returns_5d
            else 0.0
        )
        avg_mr30 = (
            sum(all_market_returns_30d) / len(all_market_returns_30d)
            if all_market_returns_30d
            else 0.0
        )

        sectors_ranked = sorted(
            all_sector_impacts.items(),
            key=lambda x: sum(x[1]) / len(x[1]),
            reverse=True,
        )

        return {
            "avg_volatility_change_pct": round(avg_vol, 2),
            "avg_market_return_5d": round(avg_mr5, 2),
            "avg_market_return_30d": round(avg_mr30, 2),
            "sectors_by_impact": [
                {"sector": s, "avg_similarity": round(sum(v) / len(v), 4)}
                for s, v in sectors_ranked
            ],
            "most_common_bullish": [
                {"ticker": t, "count": c} for t, c in most_common_bullish
            ],
            "most_common_bearish": [
                {"ticker": t, "count": c} for t, c in most_common_bearish
            ],
            "total_events_analyzed": len(results),
        }

    # ── Collection Management ──────────────────────────────────────

    async def get_collection_stats(
        self,
        collection: str = HISTORICAL_COLLECTION,
    ) -> Dict[str, Any]:
        try:
            count = await self.chroma.count(collection)
            return {
                "collection": collection,
                "document_count": count,
                "embedding_dimension": self.embeddings.get_dimension(),
                "cache_stats": self.cache.stats(),
            }
        except Exception as e:
            logger.error("Failed to get collection stats: %s", e)
            return {
                "collection": collection,
                "document_count": 0,
                "error": str(e),
            }

    async def delete_event(
        self,
        event_id: str,
        collection: str = HISTORICAL_COLLECTION,
    ) -> bool:
        try:
            collection_obj = await self.chroma.get_or_create_collection(collection)
            await collection_obj.delete(ids=[event_id])
            return True
        except Exception as e:
            logger.error("Failed to delete event %s: %s", event_id[:8], e)
            return False

    async def close(self) -> None:
        await self.cache.save_to_disk()
        await self.chroma.close()
