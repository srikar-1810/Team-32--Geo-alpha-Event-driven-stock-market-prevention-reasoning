from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import streamlit as st


def render_event_timeline(events: List[Dict[str, Any]]) -> None:
    if not events:
        st.info("No events to display.")
        return

    for event in events:
        severity = event.get("severity", 0.5)
        color = "🔴" if severity >= 0.7 else "🟡" if severity >= 0.4 else "🟢"
        title = event.get("title", "Untitled")
        date_str = event.get("event_date", "")
        if isinstance(date_str, str):
            try:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                date_str = dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                pass

        with st.container():
            cols = st.columns([1, 8, 2])
            with cols[0]:
                st.markdown(f"**{color}**")
            with cols[1]:
                st.markdown(f"**{title}**")
                desc = event.get("description", "")[:150]
                if desc:
                    st.caption(desc)
                actors = event.get("actors", [])
                if actors:
                    st.caption(f"Actors: {', '.join(actors[:3])}")
            with cols[2]:
                st.caption(f"{date_str}")
                st.caption(f"Severity: {severity:.2f}")
            st.divider()
