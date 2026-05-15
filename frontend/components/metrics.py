"""Polished UI components for institutional-grade dashboard."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import streamlit as st


def metric_card(
    label: str,
    value: str,
    delta: Optional[str] = None,
    help_text: Optional[str] = None,
    color: Optional[str] = None,
) -> None:
    css = ""
    if color == "green":
        css = "background: linear-gradient(135deg, rgba(46,204,113,0.12) 0%, rgba(46,204,113,0.04) 100%); border-left: 3px solid #2ecc71;"
    elif color == "red":
        css = "background: linear-gradient(135deg, rgba(231,76,60,0.12) 0%, rgba(231,76,60,0.04) 100%); border-left: 3px solid #e74c3c;"
    elif color == "blue":
        css = "background: linear-gradient(135deg, rgba(52,152,219,0.12) 0%, rgba(52,152,219,0.04) 100%); border-left: 3px solid #3498db;"
    elif color == "gold":
        css = "background: linear-gradient(135deg, rgba(241,196,15,0.12) 0%, rgba(241,196,15,0.04) 100%); border-left: 3px solid #f1c40f;"
    else:
        css = "background: rgba(255,255,255,0.03); border-left: 3px solid #5dade2;"

    st.markdown(
        f"""<div style="{css} border-radius: 6px; padding: 12px 16px; margin: 4px 0;">
<div style="color: #95a5a6; font-size: 0.75rem; font-weight: 500; letter-spacing: 0.5px; text-transform: uppercase;">{label}</div>
<div style="color: #ecf0f1; font-size: 1.6rem; font-weight: 700; line-height: 1.2;">{value}</div>
{f'<div style="color: #2ecc71; font-size: 0.8rem; font-weight: 500;">▲ {delta}</div>' if delta and ('+' in delta or delta.startswith('▲')) else ''}
{f'<div style="color: #e74c3c; font-size: 0.8rem; font-weight: 500;">▼ {delta}</div>' if delta and ('-' in delta or delta.startswith('▼')) else ''}
</div>""",
        unsafe_allow_html=True,
    )


def confidence_meter(value: float, label: str = "Confidence") -> str:
    pct = int(value * 100)
    bar_color = "#2ecc71" if value >= 0.7 else "#f1c40f" if value >= 0.4 else "#e74c3c"
    return f"""
<div style="margin: 8px 0;">
<div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #95a5a6; margin-bottom: 4px;">
<span>{label}</span>
<span>{pct}%</span>
</div>
<div style="background: #2c3e50; border-radius: 4px; height: 6px; overflow: hidden;">
<div style="background: {bar_color}; width: {pct}%; height: 100%; border-radius: 4px; transition: width 0.6s ease;"></div>
</div>
</div>"""


def stock_card(
    ticker: str,
    company: str,
    direction: str,
    relevance: float,
    sector: str,
    reasoning: str,
) -> str:
    is_bullish = direction == "bullish"
    border = "#2ecc71" if is_bullish else "#e74c3c"
    icon = "🟢" if is_bullish else "🔴"
    label = "BULLISH" if is_bullish else "BEARISH"

    return f"""
<div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-left: 3px solid {border}; border-radius: 8px; padding: 14px; margin: 6px 0;">
<div style="display: flex; justify-content: space-between; align-items: center;">
<div>
<span style="font-size: 1.1rem; font-weight: 700; color: #ecf0f1;">{ticker}</span>
<span style="font-size: 0.75rem; color: #95a5a6; margin-left: 8px;">{company}</span>
</div>
<span style="font-size: 0.7rem; font-weight: 600; color: {border}; background: rgba({','.join(str(ord(c)) for c in border[1:])},0.1); padding: 2px 8px; border-radius: 4px;">{icon} {label}</span>
</div>
<div style="display: flex; gap: 16px; margin-top: 8px;">
<span style="font-size: 0.75rem; color: #7f8c8d;">{sector}</span>
<span style="font-size: 0.75rem; color: #7f8c8d;">Relevance: {relevance:.2f}</span>
</div>
<div style="font-size: 0.8rem; color: #bdc3c7; margin-top: 6px;">{reasoning[:80]}{'...' if len(reasoning) > 80 else ''}</div>
</div>"""


def event_card(event: Dict[str, Any]) -> str:
    sev = event.get("severity", event.get("severity_estimate", 5))
    title = event.get("title", event.get("event_title", "Unknown"))
    loc = event.get("location", "Unknown")
    etype = event.get("event_type", "")
    desc = event.get("description", event.get("event_description", ""))[:120]
    source = event.get("source", "GDELT")

    if sev >= 8:
        badge = '<span style="background:#e74c3c;color:white;padding:1px 8px;border-radius:3px;font-size:0.65rem;font-weight:600;">CRITICAL</span>'
        border = "#e74c3c"
    elif sev >= 6:
        badge = '<span style="background:#e67e22;color:white;padding:1px 8px;border-radius:3px;font-size:0.65rem;font-weight:600;">HIGH</span>'
        border = "#e67e22"
    elif sev >= 4:
        badge = '<span style="background:#f1c40f;color:#2c3e50;padding:1px 8px;border-radius:3px;font-size:0.65rem;font-weight:600;">MEDIUM</span>'
        border = "#f1c40f"
    else:
        badge = '<span style="background:#2ecc71;color:white;padding:1px 8px;border-radius:3px;font-size:0.65rem;font-weight:600;">LOW</span>'
        border = "#2ecc71"

    return f"""
<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-left:3px solid {border};border-radius:8px;padding:12px 16px;margin:6px 0;">
<div style="display:flex;justify-content:space-between;align-items:center;">
<span style="font-weight:600;color:#ecf0f1;font-size:0.9rem;">{title[:60]}</span>
{badge}
</div>
<div style="display:flex;gap:12px;margin-top:4px;font-size:0.75rem;color:#7f8c8d;">
<span>📍 {loc[:30]}</span>
<span>🏷️ {etype}</span>
<span>📡 {source}</span>
<span>⚡ {sev:.1f}/10</span>
</div>
{f'<div style="font-size:0.8rem;color:#bdc3c7;margin-top:6px;">{desc}</div>' if desc else ''}
</div>"""


def pipeline_status_card(name: str, status: str, detail: str = "") -> str:
    colors = {"healthy": "#2ecc71", "running": "#3498db", "error": "#e74c3c",
              "degraded": "#e67e22", "idle": "#95a5a6", "pending": "#f1c40f"}
    color = colors.get(status.lower(), "#95a5a6")
    dots = {"healthy": "●", "running": "◉", "error": "◆", "degraded": "▲", "idle": "○", "pending": "◎"}
    dot = dots.get(status.lower(), "○")

    return f"""
<div style="display:flex;align-items:center;justify-content:space-between;padding:8px 12px;margin:2px 0;background:rgba(255,255,255,0.02);border-radius:4px;">
<div>
<span style="color:{color};font-size:1rem;margin-right:8px;">{dot}</span>
<span style="color:#ecf0f1;font-size:0.8rem;font-weight:500;">{name}</span>
</div>
<div>
<span style="color:{color};font-size:0.7rem;font-weight:600;">{status.upper()}</span>
{f'<span style="color:#7f8c8d;font-size:0.7rem;margin-left:8px;">{detail}</span>' if detail else ''}
</div>
</div>"""


def section_header(title: str, subtitle: Optional[str] = None) -> None:
    st.markdown(f"""
<div style="margin: 16px 0 8px 0;">
<div style="display:flex;align-items:center;gap:8px;">
<div style="width:3px;height:18px;background:#3498db;border-radius:2px;"></div>
<h3 style="color:#ecf0f1;font-size:1.05rem;font-weight:600;margin:0;padding:0;">{title}</h3>
</div>
{f'<p style="color:#7f8c8d;font-size:0.8rem;margin:4px 0 0 12px;">{subtitle}</p>' if subtitle else ''}
</div>
""", unsafe_allow_html=True)


def ai_reasoning_panel(title: str, content: str, key_drivers: List[str] = None, confidence: float = 0.0) -> None:
    drivers_html = ""
    if key_drivers:
        drivers_list = "".join(
            f'<span style="background:rgba(52,152,219,0.15);color:#3498db;padding:2px 10px;border-radius:12px;font-size:0.75rem;">{d}</span>'
            for d in key_drivers
        )
        drivers_html = f"""
        <div style="margin-top:10px;padding-top:10px;border-top:1px solid rgba(255,255,255,0.06);">
            <span style="color:#7f8c8d;font-size:0.7rem;font-weight:600;">KEY DRIVERS</span>
            <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:6px;">
                {drivers_list}
            </div>
        </div>
        """

    confidence_html = f'<span style="margin-left:auto;font-size:0.7rem;color:#95a5a6;">confidence: {confidence:.0%}</span>' if confidence else ''

    st.markdown(f"""
<div style="background:linear-gradient(135deg,rgba(52,152,219,0.08) 0%,rgba(52,152,219,0.02) 100%);border:1px solid rgba(52,152,219,0.2);border-radius:8px;padding:16px;margin:8px 0;">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
<span style="font-size:1.2rem;">🧠</span>
<span style="color:#ecf0f1;font-weight:600;font-size:0.95rem;">AI {title}</span>
{confidence_html}
</div>
<div style="color:#bdc3c7;font-size:0.85rem;line-height:1.5;">{content}</div>
{drivers_html}
</div>
""", unsafe_allow_html=True)


def severity_badge(severity: float) -> str:
    if severity >= 0.7:
        return "🔴 HIGH"
    if severity >= 0.4:
        return "🟡 MEDIUM"
    return "🟢 LOW"


def agent_status_badge(agent_type: str, status: str) -> str:
    icons = {"running": "🔄", "completed": "✅", "failed": "❌", "error": "❌",
             "pending": "⏳", "idle": "💤", "healthy": "✅", "degraded": "⚠️"}
    icon = icons.get(status.lower(), "❓")
    colors = {"running": "#3498db", "completed": "#2ecc71", "failed": "#e74c3c",
              "error": "#e74c3c", "pending": "#f1c40f", "idle": "#95a5a6",
              "healthy": "#2ecc71", "degraded": "#e67e22"}
    color = colors.get(status.lower(), "#95a5a6")
    return f'<span style="color:{color};font-size:0.75rem;font-weight:600;">{icon} {agent_type}: {status.upper()}</span>'


def status_badge(status: str) -> str:
    icons = {"healthy": "✅", "completed": "✅", "running": "🔄", "failed": "❌",
             "error": "❌", "pending": "⏳", "idle": "💤", "degraded": "⚠️"}
    icon = icons.get(status.lower(), "❓")
    return f"{icon} {status.upper()}"
