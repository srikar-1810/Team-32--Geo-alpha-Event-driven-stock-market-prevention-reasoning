import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from app.services.ingestion.storage import geopol_storage
from app.models.geopol_event import GeoPolEvent
from app.models.sentiment import SentimentData

async def seed_master_data():
    print("🚀 Starting Master Seeding (Production Mode)...")
    
    # 1. Geopolitical Events
    print("  - Seeding Geopolitical Events...")
    events = [
        GeoPolEvent(
            source="gdelt",
            title="Energy Pipeline Disruption in North Sea",
            description="A major subsea pipeline has experienced a pressure drop. Possible sabotage suspected.",
            event_date=datetime.now(timezone.utc) - timedelta(hours=2),
            location="Norway/UK",
            event_type="crisis",
            severity=0.92,
            actors=["Norway", "UK", "Russia"],
            affected_sectors=["energy", "utilities"],
            source_url="https://example.com/news/1"
        ),
        GeoPolEvent(
            source="gdelt",
            title="New Trade Sanctions on Semiconductor Exports",
            description="The US Treasury announced new round of sanctions targeting advanced AI chips.",
            event_date=datetime.now(timezone.utc) - timedelta(hours=5),
            location="Washington D.C.",
            event_type="sanctions",
            severity=0.78,
            actors=["USA", "China"],
            affected_sectors=["technology", "finance"],
            source_url="https://example.com/news/2"
        )
    ]
    await geopol_storage.save_events(events)
    
    # 2. Sentiment Data
    print("  - Seeding Sentiment Data...")
    sentiment_posts = [
        SentimentData(
            platform="reddit",
            subreddit="wallstreetbets",
            post_id="post_1",
            title="Bullish on NVDA earnings",
            text="AI demand is insane. NVDA is going to the moon.",
            created_utc=datetime.now(timezone.utc) - timedelta(hours=1),
            sentiment_score=0.85,
            sentiment_label="bullish",
            confidence=0.92,
            tickers_mentioned=["NVDA", "AI"]
        ),
        SentimentData(
            platform="reddit",
            subreddit="stocks",
            post_id="post_2",
            title="Worried about inflation impact",
            text="Rates higher for longer will hurt tech. Looking bearish on QQQ.",
            created_utc=datetime.now(timezone.utc) - timedelta(hours=3),
            sentiment_score=-0.62,
            sentiment_label="bearish",
            confidence=0.88,
            tickers_mentioned=["QQQ", "FED"]
        ),
        SentimentData(
            platform="reddit",
            subreddit="investing",
            post_id="post_3",
            title="AAPL demand remains strong in Asia",
            text="Despite macro headwinds, iPhone sales are holding up well.",
            created_utc=datetime.now(timezone.utc) - timedelta(hours=6),
            sentiment_score=0.45,
            sentiment_label="bullish",
            confidence=0.75,
            tickers_mentioned=["AAPL"]
        )
    ]
    await geopol_storage.save_sentiment(sentiment_posts)
    
    # 3. Market Data
    print("  - Seeding Market Data...")
    market_data = [
        {"date": (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d"), 
         "open": 500 + i, "high": 505 + i, "low": 495 + i, "close": 502 + i, "volume": 50000000}
        for i in range(30)
    ]
    await geopol_storage.save_market_data("SPY", market_data)
    await geopol_storage.save_market_data("AAPL", market_data)
    await geopol_storage.save_market_data("NVDA", market_data)
    
    print("✅ Master Seeding Complete.")

if __name__ == "__main__":
    asyncio.run(seed_master_data())
