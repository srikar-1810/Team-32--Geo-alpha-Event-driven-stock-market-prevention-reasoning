from __future__ import annotations

import os
from typing import Any, AsyncGenerator, Dict

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Must set env vars before importing app modules
os.environ.setdefault("TIINGO_API_TOKEN", "test_token")
os.environ.setdefault("REDDIT_CLIENT_ID", "test_id")
os.environ.setdefault("REDDIT_CLIENT_SECRET", "test_secret")
os.environ.setdefault("OPENAI_API_KEY", "test_key")
os.environ.setdefault("SECRET_KEY", "test_secret_key_for_testing")

from app.config import settings


@pytest.fixture(scope="session")
def event_loop():
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def db_session():
    from app.db.session import async_session_factory
    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def sample_geopol_event() -> Dict[str, Any]:
    return {
        "source": "gdelt",
        "title": "Test Geopolitical Event",
        "description": "A test event for unit testing",
        "event_date": "2024-01-01T00:00:00Z",
        "location": "TestRegion",
        "event_type": "conflict",
        "severity": 0.7,
        "actors": ["ActorA", "ActorB"],
        "affected_sectors": ["energy", "defense"],
        "source_url": "https://example.com/test",
    }


@pytest.fixture
def sample_reddit_post() -> Dict[str, Any]:
    return {
        "id": "test_post_123",
        "title": "Bullish on AAPL earnings",
        "text": "AAPL is going to moon! Great earnings report. Buying more calls.",
        "score": 150,
        "num_comments": 25,
        "subreddit": "wallstreetbets",
        "created_utc": "2024-01-01T12:00:00Z",
    }


@pytest.fixture
def sample_market_data() -> Dict[str, Any]:
    return {
        "date": "2024-01-01",
        "open": 150.0,
        "high": 155.0,
        "low": 149.0,
        "close": 154.0,
        "volume": 10000000,
        "adjClose": 154.0,
    }
