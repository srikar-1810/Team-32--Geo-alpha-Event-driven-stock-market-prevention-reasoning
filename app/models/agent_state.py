from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.models.base import Entity


class AgentState(Entity):
    agent_id: str
    agent_type: str
    status: str = "idle"
    current_task: Optional[str] = None
    model: str
    temperature: float = 0.2
    max_tokens: int = 4096
    tools: List[str] = Field(default_factory=list)
    memory: Dict[str, Any] = Field(default_factory=dict)
    error_count: int = 0
    tasks_completed: int = 0
    last_heartbeat: Optional[datetime] = None


class AgentExecution(Entity):
    agent_id: str
    execution_id: str
    workflow_type: str
    status: str = "pending"
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    tokens_used: int = 0
    cost: float = 0.0


class AgentMessage(Entity):
    agent_id: str
    execution_id: str
    role: str
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
