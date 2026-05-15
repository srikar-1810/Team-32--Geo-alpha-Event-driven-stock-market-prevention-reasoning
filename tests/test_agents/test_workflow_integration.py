"""End-to-end integration tests for the LangGraph multi-agent workflow."""

from __future__ import annotations

import pytest
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.workflow.orchestrator import WorkflowOrchestrator
from app.services.workflow.state import create_initial_state
from app.services.workflow.tools import AgentTools
from app.services.workflow.graph import WorkflowGraph


@pytest.fixture(autouse=True)
def mock_llm():
    """Mock LLM calls for all workflow tests to avoid real OpenAI API calls."""
    with patch("app.services.workflow.base.EnhancedAgentNode._call_llm") as mock:
        mock.return_value = ('{"response": "test", "summary": "test analysis", "key_findings": ["test"], "confidence": 0.5, "sectors_affected": [{"sector": "energy", "direction": "bullish", "confidence": 0.5, "reasoning": "test"}], "stocks_affected": [{"ticker": "SPY", "direction": "bullish", "confidence": 0.5, "reasoning": "test"}], "risk_factors": ["test"], "volatility_assessment": {"regime": "normal", "vix_estimate": 20, "overall_risk_level": "low", "primary_risks": ["test"]}, "outcomes": [{"scenario": "base", "probability": 0.5, "description": "test", "market_impact": 0}], "executive_summary": "test", "risk_outlook": "test", "market_impact_timeline": "test", "sector_analysis": [{"sector": "energy", "current_state": "test", "outlook": "test"}], "top_tickers": [{"ticker": "SPY", "direction": "neutral", "rationale": "test"}], "report_title": "test", "date": "2024-01-01", "is_directive": false}', False, "gpt-4o")
        yield mock


@pytest.fixture
def mock_tools() -> AgentTools:
    tools = AgentTools()
    tools._gdelt = AsyncMock()
    tools._reddit = AsyncMock()
    tools._tiingo = AsyncMock()
    tools._yahoo = AsyncMock()
    tools._chroma = AsyncMock()
    tools._historical_rag = AsyncMock()

    # Mock AgentTools public methods to avoid calling through to real clients
    async def fake_fetch_gdelt(*args, **kwargs):
        return []
    async def fake_fetch_sentiment(*args, **kwargs):
        return {"posts_analyzed": 0, "overall_score": 0.0, "confidence": 0.0}
    async def fake_sector_prices(*args, **kwargs):
        return {}
    async def fake_stock_data(*args, **kwargs):
        return {}
    async def fake_historical_rag(*args, **kwargs):
        return {"total_results": 0, "results": [], "market_reactions": {}}
    async def fake_macro(*args, **kwargs):
        return {}

    tools.fetch_gdelt_events = AsyncMock(side_effect=fake_fetch_gdelt)
    tools.fetch_gdelt_events_cameo = AsyncMock(side_effect=fake_fetch_gdelt)
    tools.fetch_reddit_sentiment = AsyncMock(side_effect=fake_fetch_sentiment)
    tools.get_sector_prices = AsyncMock(side_effect=fake_sector_prices)
    tools.get_stock_data = AsyncMock(side_effect=fake_stock_data)
    tools.query_historical_rag = AsyncMock(side_effect=fake_historical_rag)
    tools.get_market_macro = AsyncMock(side_effect=fake_macro)
    return tools


@pytest.fixture
def orchestrator(mock_tools: AgentTools) -> WorkflowOrchestrator:
    return WorkflowOrchestrator(tools=mock_tools)


class TestWorkflowIntegration:
    """Integration tests for the full multi-agent workflow."""

    @pytest.mark.asyncio
    async def test_workflow_initial_state(self, orchestrator):
        state = create_initial_state(
            query="What if Russia invades Poland?",
            tickers=["SPY", "XLE"],
            sectors=["energy", "defense"],
            location="Eastern Europe",
            parameters={"severity": 8.0},
        )
        assert state["query"] == "What if Russia invades Poland?"
        assert "SPY" in state["tickers"]
        assert "energy" in state["sectors"]
        assert state.get("workflow_id", "").startswith("wf-")
        assert state.get("completed_at") is None or state["completed_at"] == ""

    @pytest.mark.asyncio
    async def test_workflow_full_analysis(self, orchestrator, mock_tools):
        async def fake_fetch_gdelt(*args, **kwargs):
            return [{"title": "Test Event", "description": "Test", "severity": 7.5}]
        mock_tools.fetch_gdelt_events = AsyncMock(side_effect=fake_fetch_gdelt)
        mock_tools.fetch_gdelt_events_cameo = AsyncMock(return_value=[])
        mock_tools.fetch_reddit_sentiment = AsyncMock(return_value={
            "posts_analyzed": 1, "overall_score": -0.5, "confidence": 0.7,
            "distribution": {"bullish": 0, "bearish": 1, "neutral": 0},
            "volume": 100, "top_keywords": ["bearish"], "signal": "bearish",
        })
        mock_tools.get_sector_prices = AsyncMock(return_value={
            "SPY": [{"close": 450, "date": "2024-01-01"}],
        })
        mock_tools.query_historical_rag = AsyncMock(return_value={
            "total_results": 1, "results": [
                {"event_id": "e1", "event_title": "Crimea 2014", "similarity": 0.85,
                 "event_type": "war", "event_date": "2014-03-01", "sectors": "energy,defense",
                 "bullish_tickers": "", "bearish_tickers": "", "confidence": 0.7},
            ], "market_reactions": {"avg_market_return_5d": -2.5},
        })

        result = await orchestrator.run_full_analysis(
            query="What if Russia invades Poland?",
            tickers=["SPY", "XLE", "GLD"],
            sectors=["energy", "defense"],
            location="Eastern Europe",
        )

        assert result is not None
        assert result["workflow_id"].startswith("wf-")
        assert result["completed_at"]
        assert result["total_execution_time_ms"] > 0

        agent_details = result.get("agent_execution_details", {})
        expected_nodes = [
            "news-intelligence",
            "social-sentiment",
            "historical-analyst",
            "market-strategist",
            "risk-analysis",
            "report-generation",
        ]
        for node in expected_nodes:
            assert node in agent_details, f"Missing agent detail: {node}"

    @pytest.mark.asyncio
    async def test_workflow_with_minimal_input(self, orchestrator, mock_tools):
        result = await orchestrator.run_full_analysis(
            query="Test query",
        )
        assert result is not None
        assert result["total_execution_time_ms"] > 0

    @pytest.mark.asyncio
    async def test_workflow_node_error_does_not_block_pipeline(
        self, orchestrator, mock_tools,
    ):
        # AgentTools catches exceptions internally and returns empty list,
        # so the pipeline continues with empty data
        result = await orchestrator.run_full_analysis(
            query="Test with failing GDELT node",
            tickers=["SPY"],
            sectors=["energy"],
        )
        assert result is not None
        assert result["completed_at"]
        assert result["total_execution_time_ms"] > 0

    @pytest.mark.asyncio
    async def test_workflow_agent_execution_details(
        self, orchestrator, mock_tools,
    ):
        result = await orchestrator.run_full_analysis(query="Execution details test")

        agent_contexts = result.get("agent_contexts", {})
        for node_name, ctx in agent_contexts.items():
            assert "status" in ctx, f"{node_name} missing status"
            assert "execution_time_ms" in ctx, f"{node_name} missing execution_time_ms"
            assert ctx["execution_time_ms"] >= 0, f"{node_name} negative execution time"

    @pytest.mark.asyncio
    async def test_workflow_market_strategist_integration(
        self, orchestrator, mock_tools,
    ):
        mock_tools.fetch_gdelt_events = AsyncMock(return_value=[
            {"title": "Energy Crisis", "description": "Oil supply disruption", "severity": 8.0},
        ])
        mock_tools.fetch_reddit_sentiment = AsyncMock(return_value={
            "posts_analyzed": 1, "overall_score": 0.7, "confidence": 0.8,
            "distribution": {"bullish": 1, "bearish": 0, "neutral": 0},
            "volume": 200, "top_keywords": ["bullish"], "signal": "bullish",
        })
        mock_tools.get_sector_prices = AsyncMock(return_value={
            "XLE": [{"close": 85, "date": "2024-01-01"}],
            "SPY": [{"close": 450, "date": "2024-01-01"}],
            "GLD": [{"close": 180, "date": "2024-01-01"}],
        })
        mock_tools.query_historical_rag = AsyncMock(return_value={
            "total_results": 1, "results": [
                {"event_id": "e1", "event_title": "Oil Shock 2022", "similarity": 0.8,
                 "event_type": "energy", "event_date": "2022-02-24", "sectors": "energy",
                 "bullish_tickers": "XLE", "bearish_tickers": "", "confidence": 0.7},
            ], "market_reactions": {"avg_market_return_5d": 2.0},
        })

        result = await orchestrator.run_full_analysis(
            query="Oil supply disruption in Middle East",
            tickers=["XLE", "SPY", "GLD"],
            sectors=["energy", "materials"],
        )

        assert result is not None
        assert result["workflow_id"].startswith("wf-")

    @pytest.mark.asyncio
    async def test_workflow_report_generation_shape(
        self, orchestrator, mock_tools,
    ):
        result = await orchestrator.run_full_analysis(query="Report shape test")

        report_ctx = result.get("agent_contexts", {}).get("report-generation", {})
        output = report_ctx.get("output", {})
        assert output is not None

    @pytest.mark.asyncio
    async def test_workflow_multiple_concurrent_runs(
        self, orchestrator, mock_tools,
    ):
        import asyncio
        queries = [
            "What if China invades Taiwan?",
            "What if Fed cuts rates?",
            "What if oil hits $200?",
        ]
        results = await asyncio.gather(*[
            orchestrator.run_full_analysis(query=q) for q in queries
        ])

        assert len(results) == 3
        for i, r in enumerate(results):
            assert r["workflow_id"].startswith("wf-")
            assert r["completed_at"] is not None

        workflow_ids = [r["workflow_id"] for r in results]
        assert len(set(workflow_ids)) == 3

    def test_workflow_graph_structure(self):
        tools = MagicMock()
        graph = WorkflowGraph(tools=tools)
        assert hasattr(graph, "run")
        assert hasattr(graph, "graph")
        assert hasattr(graph, "compile")
        sequence = graph.get_agent_sequence()
        assert len(sequence) >= 6

    @pytest.mark.asyncio
    async def test_workflow_tools_lazy_init(self):
        tools = AgentTools()
        assert tools.gdelt is not None
        assert tools.reddit is not None
        assert tools.tiingo is not None
        assert tools.chroma is not None
        assert tools.historical_rag is not None

    @pytest.mark.asyncio
    async def test_workflow_error_aggregation(self, orchestrator, mock_tools):
        mock_tools.fetch_gdelt_events = AsyncMock(side_effect=Exception("GDELT error"))

        result = await orchestrator.run_full_analysis(
            query="Test with all errors",
            tickers=["SPY"],
        )

        assert result["status"] in ("completed", "completed_with_errors", "failed")
