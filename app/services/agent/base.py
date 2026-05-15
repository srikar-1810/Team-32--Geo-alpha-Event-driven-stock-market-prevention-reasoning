from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.config import settings
from app.logging_config import get_logger


class BaseAgent(ABC):
    """Abstract base class for all AI agents in the GeoMarketGPT system."""

    def __init__(
        self,
        agent_id: str,
        name: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> None:
        self.agent_id = agent_id
        self.name = name
        self.model = model or settings.llm_model
        self.temperature = temperature or settings.OPENAI_TEMPERATURE
        self.max_tokens = max_tokens or settings.OPENAI_MAX_TOKENS
        self.logger = get_logger(f"agent.{agent_id}")
        self._memory: List[Dict[str, Any]] = []
        self._tools: Dict[str, Any] = {}

    def register_tool(self, name: str, tool: Any) -> None:
        self._tools[name] = tool

    def get_tool(self, name: str) -> Any:
        return self._tools.get(name)

    @abstractmethod
    async def run(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ...

    def _add_to_memory(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self._memory.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        })

    def get_memory(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self._memory[-limit:]

    def clear_memory(self) -> None:
        self._memory.clear()

    def _create_execution_id(self) -> str:
        return f"{self.agent_id}-{uuid4().hex[:12]}"

    async def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        from app.utils.llm_client import create_llm_client

        client = create_llm_client()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if tools:
            kwargs["tools"] = tools

        response = await client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""
