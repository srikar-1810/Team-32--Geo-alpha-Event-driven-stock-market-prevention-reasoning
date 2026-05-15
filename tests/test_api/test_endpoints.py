from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "GeoMarketGPT"
    assert "version" in data
    assert "status" in data


@pytest.mark.asyncio
async def test_geopol_list_events(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/geopol/events")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_geopol_create_event(async_client: AsyncClient, sample_geopol_event: dict) -> None:
    response = await async_client.post("/api/v1/geopol/events/ingest", json=sample_geopol_event)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == sample_geopol_event["title"]
    assert data["source"] == sample_geopol_event["source"]


@pytest.mark.asyncio
async def test_geopol_summary(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/geopol/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_events" in data


@pytest.mark.asyncio
async def test_sentiment_analysis(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/sentiment/analysis", params={"query": "AAPL"})
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "AAPL"


@pytest.mark.asyncio
async def test_sentiment_trends(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/sentiment/trends", params={"hours": 24})
    assert response.status_code == 200
    data = response.json()
    assert "trend_direction" in data


@pytest.mark.asyncio
async def test_market_data(async_client: AsyncClient) -> None:
    response = await async_client.get(
        "/api/v1/markets/data/SPY",
        params={"start_date": "2024-01-01", "end_date": "2024-01-30"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_market_impact(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/markets/impact", params={"event_id": "test-event-123"})
    assert response.status_code == 200
    data = response.json()
    assert "overall_impact_score" in data


@pytest.mark.asyncio
async def test_rag_query(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/api/v1/rag/query",
        json={"query": "What is the impact of sanctions?", "collection": "geopol_events"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_agents(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/agents")
    assert response.status_code == 200
    agents = response.json()
    assert isinstance(agents, list)
    assert len(agents) > 0


@pytest.mark.asyncio
async def test_run_agent(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/api/v1/agents/run/news-intelligence",
        json={"input_data": {"query": "test analysis"}},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_generate_report(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/api/v1/reports/generate",
        json={"title": "Test Report", "format": "markdown", "sections": ["Executive Summary"]},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_reports(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/reports")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_scenario(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/api/v1/simulation/scenarios",
        json={"name": "Test Scenario", "description": "Test description"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_run_backtest(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/api/v1/backtest/run",
        json={
            "strategy": "test",
            "tickers": ["SPY"],
            "start_date": "2024-01-01",
            "end_date": "2024-01-30",
            "initial_capital": 100000.0,
        },
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_orchestrator(async_client: AsyncClient) -> None:
    response = await async_client.post(
        "/api/v1/agents/orchestrate",
        json={
            "agents": ["news-intelligence", "social-sentiment"],
            "input_data": {"query": "market analysis"},
            "workflow_type": "sequential",
        },
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_degraded(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
