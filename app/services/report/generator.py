from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.config import settings
from app.logging_config import get_logger
from app.models.report import Report
from app.services.report.templates import REPORT_TEMPLATES

logger = get_logger(__name__)


class ReportGenerator:
    """Generates reports in multiple formats from structured data."""

    OUTPUT_DIR = Path(settings.ROOT_DIR) / "output" / "reports"

    def __init__(self) -> None:
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    async def generate(
        self,
        title: str,
        sections: Dict[str, str],
        format: str = "markdown",
        metadata: Optional[Dict[str, Any]] = None,
        agent_outputs: Optional[Dict[str, Any]] = None,
    ) -> Report:
        report_id = f"report-{uuid4().hex[:12]}"

        if format == "markdown":
            content = self._render_markdown(title, sections, metadata, agent_outputs)
        elif format == "html":
            content = self._render_html(title, sections, metadata, agent_outputs)
        elif format == "json":
            content = self._render_json(title, sections, metadata, agent_outputs)
        else:
            content = self._render_markdown(title, sections, metadata, agent_outputs)

        file_path = self.OUTPUT_DIR / f"{report_id}.{format}"
        file_path.write_text(content, encoding="utf-8")

        return Report(
            title=title,
            status="completed",
            format=format,
            sections=[{"title": k, "content": v[:500], "section_type": "text", "order": i} for i, (k, v) in enumerate(sections.items())],
            parameters=metadata or {},
            file_path=str(file_path),
            file_size_bytes=file_path.stat().st_size,
        )

    def _render_markdown(
        self,
        title: str,
        sections: Dict[str, str],
        metadata: Optional[Dict[str, Any]] = None,
        agent_outputs: Optional[Dict[str, Any]] = None,
    ) -> str:
        lines = [f"# {title}", ""]
        if metadata:
            lines.append(f"*Generated: {datetime.now(timezone.utc).isoformat()}*")
            lines.append("")

        for section_title, content in sections.items():
            lines.append(f"## {section_title}")
            lines.append("")
            lines.append(content)
            lines.append("")

        if agent_outputs:
            lines.append("## Agent Analysis")
            lines.append("")
            for agent_id, output in agent_outputs.items():
                lines.append(f"### {agent_id}")
                analysis = output.get("analysis", json.dumps(output, default=str)[:300])
                lines.append(analysis)
                lines.append("")

        return "\n".join(lines)

    def _render_html(
        self,
        title: str,
        sections: Dict[str, str],
        metadata: Optional[Dict[str, Any]] = None,
        agent_outputs: Optional[Dict[str, Any]] = None,
    ) -> str:
        md = self._render_markdown(title, sections, metadata, agent_outputs)
        try:
            import markdown
            return markdown.markdown(
                md,
                extensions=["tables", "fenced_code", "codehilite"],
            )
        except ImportError:
            return f"<html><body><pre>{md}</pre></body></html>"

    def _render_json(
        self,
        title: str,
        sections: Dict[str, str],
        metadata: Optional[Dict[str, Any]] = None,
        agent_outputs: Optional[Dict[str, Any]] = None,
    ) -> str:
        data = {
            "report": {
                "title": title,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "sections": [{"title": k, "content": v} for k, v in sections.items()],
                "metadata": metadata or {},
                "agent_outputs": agent_outputs or {},
            }
        }
        return json.dumps(data, indent=2, default=str)
