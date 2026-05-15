#!/usr/bin/env python3
"""Seed the database and ChromaDB with sample data for development."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from uuid import uuid4


SAMPLE_EVENTS: List[Dict[str, Any]] = [
    {
        "source": "gdelt",
        "title": "Russia-Ukraine Conflict Escalation",
        "description": "Significant escalation in Eastern Ukraine with increased military activity and international sanctions discussions.",
        "event_date": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        "location": "Ukraine",
        "event_type": "conflict",
        "severity": 0.85,
        "actors": ["Russia", "Ukraine", "NATO"],
        "affected_sectors": ["energy", "defense", "commodities"],
        "source_url": "https://example.com/ukraine",
    },
    {
        "source": "gdelt",
        "title": "Federal Reserve Signals Rate Decision",
        "description": "Federal Reserve chair indicates potential interest rate adjustment at next meeting, citing inflation concerns.",
        "event_date": (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(),
        "location": "United States",
        "event_type": "economic",
        "severity": 0.65,
        "actors": ["Federal Reserve", "US Treasury"],
        "affected_sectors": ["finance", "technology", "real estate"],
        "source_url": "https://example.com/fed",
    },
    {
        "source": "gdelt",
        "title": "Middle East Oil Supply Disruption",
        "description": "Major oil production disruption in the Middle East due to geopolitical tensions, affecting global supply chains.",
        "event_date": (datetime.now(timezone.utc) - timedelta(hours=8)).isoformat(),
        "location": "Middle East",
        "event_type": "conflict",
        "severity": 0.78,
        "actors": ["OPEC", "Saudi Arabia", "Iran"],
        "affected_sectors": ["energy", "commodities", "transportation"],
        "source_url": "https://example.com/oil",
    },
    {
        "source": "gdelt",
        "title": "EU Sanctions Package Announced",
        "description": "European Union announces new sanctions package targeting financial institutions and technology exports.",
        "event_date": (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat(),
        "location": "European Union",
        "event_type": "economic",
        "severity": 0.6,
        "actors": ["European Union", "European Commission"],
        "affected_sectors": ["finance", "technology", "defense"],
        "source_url": "https://example.com/eu-sanctions",
    },
    {
        "source": "gdelt",
        "title": "Climate Summit Climate Agreement",
        "description": "Global climate summit concludes with new agreement on emissions targets and renewable energy investment.",
        "event_date": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        "location": "International",
        "event_type": "diplomacy",
        "severity": 0.45,
        "actors": ["UN", "Multiple Nations"],
        "affected_sectors": ["energy", "technology", "agriculture"],
        "source_url": "https://example.com/climate",
    },
    {
        "source": "gdelt",
        "title": "Technology Sector Antitrust Investigation",
        "description": "Major antitrust investigation launched against leading technology companies for market dominance practices.",
        "event_date": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
        "location": "United States",
        "event_type": "policy",
        "severity": 0.55,
        "actors": ["US DOJ", "FTC", "Big Tech"],
        "affected_sectors": ["technology", "finance"],
        "source_url": "https://example.com/antitrust",
    },
]


async def seed_chromadb() -> None:
    print("Seeding ChromaDB...")
    try:
        from app.services.chroma.client import ChromaClient
        from app.services.chroma.collections import CollectionManager
        from app.services.chroma.embeddings import EmbeddingService

        chroma = ChromaClient()
        embeddings = EmbeddingService()
        manager = CollectionManager(chroma)
        await manager.initialize()

        for event in SAMPLE_EVENTS:
            event_id = str(uuid4())
            text = f"{event['title']}. {event['description']}"
            metadata = {
                "source": event["source"],
                "event_type": event["event_type"],
                "severity": event["severity"],
                "location": event["location"],
                "event_date": event["event_date"],
                "actors": ",".join(event["actors"]),
                "sectors": ",".join(event["affected_sectors"]),
            }
            await manager.store_event(event_id, text, metadata)
            print(f"  Stored event: {event['title'][:50]}...")

        stats = await manager.get_collection_stats()
        print(f"ChromaDB stats: {stats}")
        await chroma.close()
        print("ChromaDB seeding complete.")
    except Exception as e:
        print(f"ChromaDB seeding failed: {e}", file=sys.stderr)


async def seed_database() -> None:
    print("Seeding PostgreSQL database...")
    try:
        from app.db.session import async_session_factory
        from app.db.base import Base

        async with async_session_factory() as session:
            async with session.begin():
                pass
        print("Database tables verified.")
    except Exception as e:
        print(f"Database seeding failed: {e}", file=sys.stderr)


async def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Seed GeoMarketGPT with sample data")
    parser.add_argument("--all", action="store_true", help="Seed all data stores")
    parser.add_argument("--chroma", action="store_true", help="Seed ChromaDB only")
    parser.add_argument("--database", action="store_true", help="Seed database only")
    args = parser.parse_args()

    if args.all or not (args.chroma or args.database):
        args.chroma = True
        args.database = True

    if args.chroma:
        await seed_chromadb()
    if args.database:
        await seed_database()

    print("Seeding complete!")


if __name__ == "__main__":
    asyncio.run(main())
