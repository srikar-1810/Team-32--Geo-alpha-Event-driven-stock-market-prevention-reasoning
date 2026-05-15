from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.logging_config import get_logger
from app.services.workflow.graph import WorkflowGraph
from app.services.workflow.state import WorkflowState, create_initial_state
from app.services.workflow.tools import AgentTools

logger = get_logger(__name__)


class WorkflowOrchestrator:
    """High-level orchestrator for the LangGraph multi-agent workflow."""

    def __init__(self, tools: Optional[AgentTools] = None) -> None:
        self.tools = tools or AgentTools()
        self.graph = WorkflowGraph(tools=self.tools)
        self._workflow_count: int = 0

    async def run_full_analysis(
        self,
        query: str,
        tickers: Optional[List[str]] = None,
        sectors: Optional[List[str]] = None,
        location: str = "",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run the complete multi-agent intelligence workflow."""
        start = time.perf_counter()
        self._workflow_count += 1
        workflow_id = f"wf-{uuid4().hex[:12]}"

        logger.info(
            "Workflow %s START: query=%s, tickers=%s, sectors=%s",
            workflow_id, query[:60], tickers, sectors,
        )

        state = create_initial_state(
            query=query,
            tickers=tickers or [],
            sectors=sectors or [],
            location=location,
            parameters=parameters or {},
        )
        state["workflow_id"] = workflow_id

        try:
            result_state = await self.graph.run(state)

            elapsed = (time.perf_counter() - start) * 1000
            result_state["completed_at"] = datetime.now(timezone.utc).isoformat()
            result_state["total_execution_time_ms"] = round(elapsed, 2)

            agent_contexts = result_state.get("agent_contexts", {})
            completed = sum(
                1 for c in agent_contexts.values()
                if isinstance(c, dict) and c.get("status") == "completed"
            )
            failed = sum(
                1 for c in agent_contexts.values()
                if isinstance(c, dict) and c.get("status") == "failed"
            )

            logger.info(
                "Workflow %s COMPLETE: %d agents completed, %d failed, %.0fms",
                workflow_id, completed, failed, elapsed,
            )

            return self._format_output(result_state, workflow_id)

        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error("Workflow %s FAILED: %s", workflow_id, e)

            return {
                "workflow_id": workflow_id,
                "status": "failed",
                "error": str(e),
                "query": query,
                "tickers": tickers or [],
                "total_execution_time_ms": round(elapsed, 2),
                "started_at": state.get("started_at", ""),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }

    def _format_output(
        self, state: WorkflowState, workflow_id: str,
    ) -> Dict[str, Any]:
        agent_contexts = state.get("agent_contexts", {})
        errors = state.get("errors", [])

        completed_count = sum(
            1 for c in agent_contexts.values()
            if isinstance(c, dict) and c.get("status") == "completed"
        )
        total_count = max(len(agent_contexts), 1)

        report = state.get("report")
        if report and isinstance(report, dict):
            report_clean = {
                k: v for k, v in report.items()
                if not k.startswith("_")
            }
        else:
            report_clean = None

        return {
            "workflow_id": workflow_id,
            "status": "completed" if not errors else "completed_with_errors",
            "query": state.get("query", ""),
            "tickers": state.get("tickers", []),
            "total_execution_time_ms": state.get("total_execution_time_ms", 0),
            "started_at": state.get("started_at", ""),
            "completed_at": state.get("completed_at", ""),
            "agent_summary": {
                "total": total_count,
                "completed": completed_count,
                "failed": total_count - completed_count,
            },
            "analyses": {
                "news_intelligence": self._safe_output(state.get("news_analysis")),
                "social_sentiment": self._safe_output(state.get("sentiment_analysis")),
                "historical_analyst": self._clean_historical(state.get("historical_analysis")),
                "market_strategist": self._safe_output(state.get("market_analysis")),
                "risk_analysis": self._safe_output(state.get("risk_assessment")),
            },
            "report": report_clean,
            "errors": errors[:10] if errors else [],
            "agent_execution_details": {
                aid: {
                    "status": ctx.get("status", "unknown"),
                    "execution_time_ms": ctx.get("execution_time_ms", 0),
                    "model_used": ctx.get("model_used", ""),
                    "fallback_used": ctx.get("fallback_used", False),
                    "tokens_used": ctx.get("tokens_used", 0),
                }
                for aid, ctx in agent_contexts.items()
                if isinstance(ctx, dict)
            },
        }

    @staticmethod
    def _safe_output(data: Any) -> Any:
        if data is None:
            return {}
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if not k.startswith("_")}
        return data

    @staticmethod
    def _clean_historical(data: Any) -> Dict[str, Any]:
        if data is None:
            return {}
        if isinstance(data, dict):
            return {
                k: v for k, v in data.items()
                if not k.startswith("_")
            }
        return {}

    async def close(self) -> None:
        await self.tools.close_all()

    @property
    def workflow_count(self) -> int:
        return self._workflow_count
