from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.logging_config import get_logger
from app.services.agent.base import BaseAgent
from app.services.agent.geopol_agent import GeopoliticalAnalystAgent
from app.services.agent.market_agent import MarketAnalystAgent
from app.services.agent.rag_agent import RAGRetrievalAgent
from app.services.agent.report_agent import ReportGeneratorAgent
from app.services.agent.sentiment_agent import SentimentAnalystAgent
from app.services.agent.simulation_agent import SimulationAgent

logger = get_logger(__name__)


class AgentOrchestrator:
    """Orchestrates multi-agent workflows for geopolitical financial analysis."""

    def __init__(self) -> None:
        self.agents: Dict[str, BaseAgent] = {}
        self._register_default_agents()

    def _register_default_agents(self) -> None:
        self.register_agent(GeopoliticalAnalystAgent())
        self.register_agent(SentimentAnalystAgent())
        self.register_agent(MarketAnalystAgent())
        self.register_agent(RAGRetrievalAgent())
        self.register_agent(ReportGeneratorAgent())
        self.register_agent(SimulationAgent())

    def register_agent(self, agent: BaseAgent) -> None:
        self.agents[agent.agent_id] = agent
        logger.info("Registered agent: %s (%s)", agent.agent_id, agent.name)

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        return self.agents.get(agent_id)

    async def run_sequential(
        self,
        agent_ids: List[str],
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        outputs = {}
        context = {"agent_outputs": {}}

        for agent_id in agent_ids:
            agent = self.get_agent(agent_id)
            if not agent:
                outputs[agent_id] = {"status": "error", "message": f"Unknown agent: {agent_id}"}
                continue

            logger.info("Running agent: %s", agent_id)
            try:
                result = await agent.run(input_data, context=context)
                outputs[agent_id] = result
                context["agent_outputs"][agent_id] = result
                context.setdefault("accumulated_output", {})[agent_id] = result
            except Exception as e:
                logger.error("Agent %s failed: %s", agent_id, e)
                outputs[agent_id] = {"status": "failed", "error": str(e)}

        return {
            "orchestration_id": f"orch-{uuid4().hex[:12]}",
            "workflow_type": "sequential",
            "agents_invoked": agent_ids,
            "outputs": outputs,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

    async def run_parallel(
        self,
        agent_ids: List[str],
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        import asyncio

        outputs = {}
        context = {"agent_outputs": {}}

        async def run_agent(agent_id: str) -> tuple[str, Dict[str, Any]]:
            agent = self.get_agent(agent_id)
            if not agent:
                return agent_id, {"status": "error", "message": f"Unknown agent: {agent_id}"}
            try:
                result = await agent.run(input_data)
                return agent_id, result
            except Exception as e:
                return agent_id, {"status": "failed", "error": str(e)}

        tasks = [run_agent(aid) for aid in agent_ids]
        results = await asyncio.gather(*tasks)

        for agent_id, result in results:
            outputs[agent_id] = result
            context["agent_outputs"][agent_id] = result

        return {
            "orchestration_id": f"orch-{uuid4().hex[:12]}",
            "workflow_type": "parallel",
            "agents_invoked": agent_ids,
            "outputs": outputs,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

    async def run_full_analysis(
        self,
        query: str,
        tickers: Optional[List[str]] = None,
        generate_report: bool = True,
    ) -> Dict[str, Any]:
        input_data = {
            "query": query,
            "tickers": tickers or [],
        }

        sequential_result = await self.run_sequential(
            agent_ids=[
                "geopol-agent",
                "sentiment-agent",
                "rag-agent",
            ],
            input_data=input_data,
        )

        market_input = {
            **input_data,
            "event_description": query,
            "days_back": 30,
        }
        market_result = await self.run_sequential(
            agent_ids=["market-agent"],
            input_data=market_input,
        )
        sequential_result["outputs"]["market-agent"] = market_result["outputs"]["market-agent"]

        if generate_report:
            report_result = await self.run_sequential(
                agent_ids=["report-agent"],
                input_data={
                    "title": f"GeoMarketGPT Analysis: {query[:50]}",
                    "template": "standard",
                    "sections": {
                        "Query": query,
                        "Tickers": ", ".join(tickers) if tickers else "N/A",
                    },
                },
                context={"agent_outputs": sequential_result["outputs"]},
            )
            sequential_result["outputs"]["report-agent"] = report_result["outputs"]["report-agent"]

        return sequential_result

    def list_agents(self) -> List[Dict[str, str]]:
        return [
            {"id": aid, "name": a.name, "type": a.__class__.__name__}
            for aid, a in self.agents.items()
        ]
