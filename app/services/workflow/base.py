from __future__ import annotations

import json
import re
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Type
from uuid import uuid4

from app.config import settings
from app.logging_config import get_logger
from app.services.workflow.state import AgentContext, AgentMemory, WorkflowState

logger = get_logger(__name__)


LLM_MODEL_TIERS: List[str] = [
    "gpt-4o",
    "gpt-4-turbo",
    "gpt-3.5-turbo",
]

FALLBACK_LLM_MODEL = "gpt-3.5-turbo"


class StructuredOutput(ABC):
    """Base for Pydantic-like structured output models."""

    @classmethod
    @abstractmethod
    def schema_prompt(cls) -> str:
        ...

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> Any:
        ...


class EnhancedAgentNode(ABC):
    """Base class for LangGraph agent nodes with full production features."""

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> None:
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.model = model or settings.llm_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.logger = get_logger(f"agent.{agent_id}")
        self._tools: Dict[str, Any] = {}
        self._execution_count: int = 0
        self._total_tokens: int = 0

    @property
    def goals(self) -> str:
        return self._goals()

    @abstractmethod
    def _goals(self) -> str:
        ...

    def register_tool(self, name: str, tool_fn: Any) -> None:
        self._tools[name] = tool_fn

    def get_tool(self, name: str) -> Any:
        return self._tools.get(name)

    @abstractmethod
    async def __call__(self, state: WorkflowState) -> WorkflowState:
        ...

    def _build_context(self, state: WorkflowState) -> str:
        ctx_parts: List[str] = []
        ctx_parts.append(f"Query: {state.get('query', '')}")
        if state.get("tickers"):
            ctx_parts.append(f"Tickers: {', '.join(state['tickers'])}")
        if state.get("sectors"):
            ctx_parts.append(f"Sectors: {', '.join(state['sectors'])}")
        if state.get("location"):
            ctx_parts.append(f"Location: {state['location']}")
        return "\n".join(ctx_parts)

    async def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: Optional[str] = None,
    ) -> Tuple[str, bool, str]:
        """Call LLM with tiered fallback. Returns (content, fallback_used, model_used)."""
        from app.utils.llm_client import create_llm_client

        full_prompt = user_prompt
        if output_schema:
            full_prompt = f"{user_prompt}\n\nYou MUST respond with valid JSON only, following this schema:\n{output_schema}"

        models_to_try = [self.model]
        if self.model != FALLBACK_LLM_MODEL and settings.LLM_PROVIDER == "openai":
            models_to_try.append(FALLBACK_LLM_MODEL)

        last_error = None
        for attempt, model in enumerate(models_to_try):
            try:
                client = create_llm_client()
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_prompt},
                ]

                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    response_format={"type": "json_object"} if output_schema else None,
                )

                content = response.choices[0].message.content or ""
                usage = response.usage
                if usage:
                    self._total_tokens += usage.total_tokens

                fallback_used = attempt > 0
                if fallback_used:
                    self.logger.warning("LLM fallback to %s used for agent %s", model, self.agent_id)

                return content, fallback_used, model

            except Exception as e:
                last_error = e
                self.logger.warning("LLM call failed with %s: %s", model, e)
                continue

        self.logger.error("All LLM tiers failed for agent %s: %s", self.agent_id, last_error)
        return "", True, "fallback_deterministic"

    def _parse_json_output(self, text: str) -> Optional[Dict[str, Any]]:
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        brace_match = re.search(r'\{[\s\S]*\}', text)
        if brace_match:
            try:
                return json.loads(brace_match.group())
            except json.JSONDecodeError:
                pass

        self.logger.warning("Failed to parse JSON from LLM output for %s", self.agent_id)
        return None

    def _build_agent_context(
        self,
        state: WorkflowState,
        output: Optional[Dict[str, Any]],
        error: Optional[str] = None,
        execution_time_ms: float = 0.0,
        fallback_used: bool = False,
        model_used: str = "",
    ) -> AgentContext:
        memory = state.get("agent_contexts", {}).get(self.agent_id, {}).get("memory", [])
        return AgentContext(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            status="completed" if not error else "failed",
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            output=output,
            error=error,
            memory=memory,
            execution_time_ms=round(execution_time_ms, 2),
            model_used=model_used or self.model,
            fallback_used=fallback_used,
            tokens_used=self._total_tokens,
        )

    def _extract_json_from_output(self, text: str, retries: int = 2) -> Optional[Dict[str, Any]]:
        for attempt in range(retries):
            parsed = self._parse_json_output(text)
            if parsed is not None:
                return parsed
            if attempt < retries - 1:
                text = (
                    f"Your previous response was not valid JSON. "
                    f"Please respond with ONLY valid JSON. No markdown, no explanation.\n\n"
                    f"Original query: {text}"
                )
        return None

    def _log_step(self, state: WorkflowState, step: str, details: str = "") -> None:
        self.logger.info(
            "[%s] %s: %s %s",
            state.get("workflow_id", "?"), self.agent_id, step, details,
        )

    def _log_error(self, state: WorkflowState, error: str) -> None:
        self.logger.error("[%s] %s ERROR: %s", state.get("workflow_id", "?"), self.agent_id, error)
        state.setdefault("errors", []).append({
            "agent": self.agent_id,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
