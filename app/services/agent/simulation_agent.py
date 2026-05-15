from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.services.agent.base import BaseAgent


class SimulationAgent(BaseAgent):
    """Runs what-if scenario simulations for geopolitical events."""

    def __init__(self) -> None:
        super().__init__(
            agent_id="simulation-agent",
            name="Scenario Simulator",
        )

    async def run(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        scenario_name = input_data.get("name", "Untitled Scenario")
        parameters = input_data.get("parameters", {})
        assumptions = input_data.get("assumptions", {})
        events = input_data.get("events", [])

        events_text = "\n".join(
            f"- {e.get('title', e)} (severity: {e.get('severity', 'N/A')})"
            for e in events[:5]
        ) if events else "No specific events."

        simulation_prompt = (
            f"Run a what-if scenario simulation:\n\n"
            f"Scenario: {scenario_name}\n\n"
            f"Parameters:\n{self._format_dict(parameters)}\n\n"
            f"Assumptions:\n{self._format_dict(assumptions)}\n\n"
            f"Triggering Events:\n{events_text}\n\n"
            f"For each sector and major market index, provide:\n"
            f"1. Projected impact direction and magnitude\n"
            f"2. Confidence interval\n"
            f"3. Time horizon (short/medium/long term)\n"
            f"4. Key risk factors\n"
            f"5. Second-order effects"
        )

        llm_output = await self._call_llm(
            system_prompt="You are a geopolitical scenario simulation analyst for a global macro hedge fund.",
            user_prompt=simulation_prompt,
        )

        scenario_id = f"scenario-{uuid4().hex[:12]}"
        self._add_to_memory("user", str(input_data))
        self._add_to_memory("assistant", llm_output)

        return {
            "agent": self.agent_id,
            "status": "completed",
            "scenario_id": scenario_id,
            "scenario_name": scenario_name,
            "simulation": llm_output,
            "parameters_used": parameters,
            "assumptions_used": assumptions,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _format_dict(d: Dict[str, Any], indent: int = 2) -> str:
        try:
            import json
            return json.dumps(d, indent=indent, default=str)
        except Exception:
            return str(d)
