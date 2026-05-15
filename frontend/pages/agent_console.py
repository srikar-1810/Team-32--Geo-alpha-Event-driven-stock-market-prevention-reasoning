from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional

import streamlit as st

from frontend.components.alerts import show_error, show_info, show_success, show_warning
from frontend.components.metrics import metric_card, agent_status_badge, section_header
from frontend.utils.api_client import api_client


def show() -> None:
    st.title("🤖 AI Agent Console")
    st.caption("Manage and monitor multi-agent AI analysis workflows.")

    tab1, tab2, tab3 = st.tabs(["🤖 Agents", "⚙️ Orchestrator", "📋 History"])

    with tab1:
        try:
            agents = asyncio.run(api_client.list_agents())
        except Exception as e:
            show_warning(f"Cannot connect to agent service: {e}")
            agents = []

        if agents:
            for agent in agents:
                with st.container():
                    cols = st.columns([2, 2, 2, 3, 2])
                    with cols[0]:
                        st.markdown(f"**{agent.get('name', 'Unknown')}**")
                    with cols[1]:
                        st.caption(agent.get("id", ""))
                    with cols[2]:
                        st.caption(agent.get("agent_type", ""))
                    with cols[3]:
                        st.caption(f"Model: {agent.get('model', 'N/A')}")
                    with cols[4]:
                        status = agent.get("status", "idle")
                        st.markdown(agent_status_badge(agent.get("agent_type", ""), status))

                    btn_cols = st.columns(2)
                    with btn_cols[0]:
                        if st.button(f"▶️ Run", key=f"run_{agent['id']}", width='stretch'):
                            st.session_state["run_agent"] = agent["id"]
                            st.session_state["run_agent_name"] = agent["name"]
                    with btn_cols[1]:
                        if st.button(f"ℹ️ Config", key=f"config_{agent['id']}", width='stretch'):
                            try:
                                config = asyncio.run(
                                    api_client._request("GET", f"/api/v1/agents/config/{agent['id']}")
                                )
                                st.json(config)
                            except Exception as e:
                                show_error(f"Config failed", str(e))
                    st.divider()
        else:
            show_info("No agents available.")

        if "run_agent" in st.session_state:
            st.subheader(f"Running: {st.session_state['run_agent_name']}")
            input_text = st.text_area(
                "Input data (JSON)",
                value=json.dumps({"query": "Analyze current geopolitical risks for energy sector"}, indent=2),
                height=150,
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🚀 Execute", type="primary"):
                    try:
                        input_data = json.loads(input_text)
                        result = asyncio.run(
                            api_client.run_agent(st.session_state["run_agent"], input_data)
                        )
                        st.success("Execution completed")
                        st.json(result)
                    except json.JSONDecodeError:
                        show_error("Invalid JSON input")
                    except Exception as e:
                        show_error("Execution failed", str(e))
            with col2:
                if st.button("❌ Cancel"):
                    del st.session_state["run_agent"]
                    st.rerun()

        st.divider()
        with st.expander("📝 Quick Actions"):
            quick_actions = {
                "Analyze Energy Sector Risk": {"agents": ["geopol-agent", "rag-agent"], "input": {"query": "Analyze geopolitical risks for energy sector including oil and gas"}},
                "Full Market Scan": {"agents": ["sentiment-agent", "market-agent"], "input": {"query": "market scan all major sectors", "tickers": ["SPY", "QQQ", "IWM", "EEM"]}},
                "Generate Briefing Report": {"agents": ["geopol-agent", "sentiment-agent", "market-agent", "report-agent"], "input": {"query": "generate daily market briefing"}},
            }

            for action_name, action_data in quick_actions.items():
                if st.button(action_name, width='stretch'):
                    try:
                        result = asyncio.run(
                            api_client.orchestrate(
                                agents=action_data["agents"],
                                input_data=action_data["input"],
                            )
                        )
                        st.success(f"{action_name} started")
                        st.json(result)
                    except Exception as e:
                        show_error(f"{action_name} failed", str(e))

    with tab2:
        st.subheader("Multi-Agent Orchestration")
        available_agents = [a.get("id") for a in agents] if agents else []
        selected = st.multiselect("Select agents to run", available_agents, default=available_agents[:3])

        workflow = st.selectbox("Workflow type", ["sequential", "parallel"])
        orchestration_input = st.text_area(
            "Input data (JSON)",
            value=json.dumps({"query": "Comprehensive geopolitical market analysis", "tickers": ["SPY", "QQQ", "XLF", "XLE"]}, indent=2),
            height=150,
        )

        if st.button("▶️ Run Orchestration", type="primary", disabled=not selected):
            try:
                input_data = json.loads(orchestration_input)
                result = asyncio.run(
                    api_client.orchestrate(agents=selected, input_data=input_data)
                )
                st.success("Orchestration completed")
                st.json(result)
            except Exception as e:
                show_error("Orchestration failed", str(e))

    with tab3:
        st.subheader("Execution History")
        st.info("Execution history will be available after running agents and orchestrations.")
