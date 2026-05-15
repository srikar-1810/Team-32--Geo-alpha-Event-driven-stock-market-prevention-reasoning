from __future__ import annotations

from typing import Any, Dict, List, Optional

from langgraph.graph import END, StateGraph

from app.logging_config import get_logger
from app.services.workflow.nodes.historical_analyst import HistoricalAnalystNode
from app.services.workflow.nodes.market_strategist import MarketStrategistNode
from app.services.workflow.nodes.news_intelligence import NewsIntelligenceNode
from app.services.workflow.nodes.report_generation import ReportGenerationNode
from app.services.workflow.nodes.risk_analysis import RiskAnalysisNode
from app.services.workflow.nodes.social_sentiment import SocialSentimentNode
from app.services.workflow.state import WorkflowState
from app.services.workflow.tools import AgentTools

logger = get_logger(__name__)

AGENT_SEQUENCE = [
    "news-intelligence",
    "social-sentiment",
    "historical-analyst",
    "market-strategist",
    "risk-analysis",
    "report-generation",
]


class WorkflowGraph:
    """LangGraph StateGraph for the multi-agent geopolitical intelligence workflow."""

    def __init__(self, tools: Optional[AgentTools] = None) -> None:
        self.tools = tools or AgentTools()
        self.graph = self._build_graph()
        self._compiled = None

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(WorkflowState)

        # ── Add nodes ──
        workflow.add_node("news-intelligence", NewsIntelligenceNode(self.tools))
        workflow.add_node("social-sentiment", SocialSentimentNode(self.tools))
        workflow.add_node("historical-analyst", HistoricalAnalystNode(self.tools))
        workflow.add_node("market-strategist", MarketStrategistNode(self.tools))
        workflow.add_node("risk-analysis", RiskAnalysisNode(self.tools))
        workflow.add_node("report-generation", ReportGenerationNode(self.tools))

        # ── Sequential edges ──
        workflow.add_edge("news-intelligence", "social-sentiment")
        workflow.add_edge("social-sentiment", "historical-analyst")
        workflow.add_edge("historical-analyst", "market-strategist")
        workflow.add_edge("market-strategist", "risk-analysis")
        workflow.add_edge("risk-analysis", "report-generation")
        workflow.add_edge("report-generation", END)

        # ── Entry point ──
        workflow.set_entry_point("news-intelligence")

        return workflow

    def compile(self):
        if self._compiled is None:
            self._compiled = self.graph.compile()
            logger.info("LangGraph workflow compiled with %d nodes", len(AGENT_SEQUENCE))
        return self._compiled

    async def run(
        self,
        initial_state: WorkflowState,
    ) -> WorkflowState:
        compiled = self.compile()
        try:
            result = await compiled.ainvoke(initial_state)
            return result
        except Exception as e:
            logger.error("LangGraph workflow execution failed: %s", e)
            initial_state["errors"].append({
                "agent": "workflow",
                "error": str(e),
                "timestamp": __import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc
                ).isoformat(),
            })
            return initial_state

    def get_agent_sequence(self) -> List[str]:
        return list(AGENT_SEQUENCE)
