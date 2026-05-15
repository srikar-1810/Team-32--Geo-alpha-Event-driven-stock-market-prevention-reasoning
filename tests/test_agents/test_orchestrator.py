from __future__ import annotations

import pytest

from app.services.agent.orchestrator import AgentOrchestrator


class TestAgentOrchestrator:
    def setup_method(self):
        self.orchestrator = AgentOrchestrator()

    def test_register_default_agents(self):
        agents = self.orchestrator.list_agents()
        assert len(agents) >= 6
        agent_ids = [a["id"] for a in agents]
        assert "geopol-agent" in agent_ids
        assert "sentiment-agent" in agent_ids
        assert "market-agent" in agent_ids
        assert "rag-agent" in agent_ids
        assert "report-agent" in agent_ids
        assert "simulation-agent" in agent_ids

    def test_get_agent(self):
        agent = self.orchestrator.get_agent("geopol-agent")
        assert agent is not None
        assert agent.agent_id == "geopol-agent"
        assert agent.name == "Geopolitical Analyst"

    def test_get_agent_unknown(self):
        agent = self.orchestrator.get_agent("nonexistent-agent")
        assert agent is None

    def test_list_agents_format(self):
        agents = self.orchestrator.list_agents()
        for a in agents:
            assert "id" in a
            assert "name" in a
            assert "type" in a
