from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.services.agent.base import BaseAgent


class ReportGeneratorAgent(BaseAgent):
    """Generates comprehensive reports from multi-agent analysis outputs."""

    REPORT_TEMPLATES = {
        "brief": "Generate a concise 1-page brief covering key findings only.",
        "standard": "Generate a standard report with executive summary, analysis, and recommendations.",
        "comprehensive": "Generate a detailed comprehensive report with full analysis, data tables, and appendix.",
        "investor_memo": "Generate an investor memo with actionable recommendations and risk assessment.",
    }

    def __init__(self) -> None:
        super().__init__(
            agent_id="report-agent",
            name="Report Generator",
        )

    async def run(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        title = input_data.get("title", "GeoMarketGPT Report")
        template = input_data.get("template", "standard")
        sections = input_data.get("sections", {})
        agent_outputs = context.get("agent_outputs", {}) if context else {}

        template_instruction = self.REPORT_TEMPLATES.get(template, self.REPORT_TEMPLATES["standard"])

        sections_text = "\n\n".join(
            f"## {k}\n{v}" for k, v in sections.items()
        )
        agents_text = "\n\n".join(
            f"### {k}\n{v.get('analysis', str(v))[:500]}"
            for k, v in agent_outputs.items()
        )

        generation_prompt = (
            f"Generate a report with the following specifications:\n\n"
            f"Title: {title}\n"
            f"Template: {template}\n"
            f"Instruction: {template_instruction}\n\n"
            f"User-defined sections:\n{sections_text}\n\n"
            f"Agent analysis outputs:\n{agents_text}\n\n"
            f"Format the report with:\n"
            f"1. Executive Summary\n"
            f"2. Key Findings\n"
            f"3. Detailed Analysis\n"
            f"4. Risk Assessment\n"
            f"5. Recommendations\n"
            f"6. Appendix (data sources, confidence levels)"
        )

        llm_output = await self._call_llm(
            system_prompt="You are a senior financial intelligence report writer.",
            user_prompt=generation_prompt,
        )

        report_id = f"report-{uuid4().hex[:12]}"
        self._add_to_memory("user", str(input_data))
        self._add_to_memory("assistant", llm_output)

        return {
            "agent": self.agent_id,
            "status": "completed",
            "report_id": report_id,
            "title": title,
            "template": template,
            "content": llm_output,
            "sections_count": len(sections),
            "word_count": len(llm_output.split()),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
