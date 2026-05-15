"""Interactive Plotly charts for institutional-grade dashboard with dark theme and animations."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

DARK_TEMPLATE = {
    "layout": {
        "font": {"color": "#bdc3c7", "family": "Helvetica, Arial, sans-serif"},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "colorway": ["#3498db", "#2ecc71", "#e74c3c", "#f1c40f", "#9b59b6", "#1abc9c", "#e67e22", "#ecf0f1"],
        "hovermode": "x unified",
        "hoverlabel": {"bgcolor": "#2c3e50", "font": {"color": "#ecf0f1", "size": 11}},
        "xaxis": {"gridcolor": "rgba(255,255,255,0.05)", "zerolinecolor": "rgba(255,255,255,0.08)", "showgrid": True},
        "yaxis": {"gridcolor": "rgba(255,255,255,0.05)", "zerolinecolor": "rgba(255,255,255,0.08)", "showgrid": True},
        "margin": {"l": 40, "r": 20, "t": 40, "b": 30},
        "legend": {"font": {"color": "#95a5a6"}, "bgcolor": "rgba(0,0,0,0)"},
    }
}


def apply_dark_theme(fig: go.Figure) -> go.Figure:
    fig.update_layout(**DARK_TEMPLATE["layout"])
    return fig


def sector_heatmap(
    sectors: List[Dict[str, Any]],
    title: str = "Sector Impact Matrix",
) -> None:
    if not sectors:
        st.info("No sector data available.")
        return

    names = [s.get("sector_name", s.get("name", ""))[:12] for s in sectors]
    magnitudes = [s.get("impact_magnitude", s.get("magnitude", 0)) for s in sectors]
    directions = [s.get("impact_direction", s.get("direction", "neutral")) for s in sectors]
    confidences = [s.get("confidence", 0.5) for s in sectors]

    dir_numeric = [1 if d == "bullish" else -1 if d == "bearish" else 0 for d in directions]
    scores = [m * d for m, d in zip(magnitudes, dir_numeric)]

    fig = go.Figure()

    fig.add_trace(go.Heatmap(
        z=[scores],
        x=names,
        y=["Impact"],
        colorscale=[
            [0.0, "#8b0000"], [0.25, "#e74c3c"], [0.45, "#7f8c8d"],
            [0.55, "#7f8c8d"], [0.75, "#2ecc71"], [1.0, "#006400"],
        ],
        zmin=-1, zmax=1,
        text=[[f"{s:.2f}" for s in scores]],
        texttemplate="%{text}",
        textfont={"size": 12, "color": "#ecf0f1"},
        hovertemplate="Sector: %{x}<br>Score: %{z:.3f}<br>Direction: %{text}<extra></extra>",
        showscale=True,
        colorbar={
            "title": {"text": "Impact", "font": {"color": "#95a5a6", "size": 10}},
            "tickfont": {"color": "#95a5a6", "size": 9},
            "len": 0.6,
            "thickness": 12,
        },
    ))

    for i, (n, m, d, c) in enumerate(zip(names, magnitudes, directions, confidences)):
        color = "#2ecc71" if d == "bullish" else "#e74c3c" if d == "bearish" else "#95a5a6"

    fig.update_layout(
        title={"text": title, "font": {"color": "#ecf0f1", "size": 13}, "x": 0.02},
        height=160,
        **{k: v for k, v in DARK_TEMPLATE["layout"].items() if k not in ("margin", "xaxis", "yaxis")},
        margin={"l": 10, "r": 60, "t": 40, "b": 10},
        xaxis={"side": "bottom", "tickangle": -30},
        yaxis={"visible": False},
    )
    fig.update_xaxes(tickfont={"size": 10, "color": "#bdc3c7"})

    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})

    cols = st.columns(len(names))
    for i, (n, m, d, c) in enumerate(zip(names, magnitudes, directions, confidences)):
        emoji = "🟢" if d == "bullish" else "🔴" if d == "bearish" else "⚪"
        cols[i].markdown(
            f"<div style='text-align:center;font-size:0.7rem;color:#95a5a6;'>"
            f"{emoji}<br><b style='color:#ecf0f1;'>{n}</b><br>{m:.2f}<br>{c:.0%}</div>",
            unsafe_allow_html=True,
        )


def sector_impact_bars(
    sectors: List[Dict[str, Any]],
    title: str = "Sector Impact Magnitude",
) -> None:
    if not sectors:
        return

    names = [s.get("sector_name", s.get("name", ""))[:14] for s in sectors]
    magnitudes = [s.get("impact_magnitude", s.get("magnitude", 0)) for s in sectors]
    directions = [s.get("impact_direction", s.get("direction", "neutral")) for s in sectors]

    colors = ["#2ecc71" if d == "bullish" else "#e74c3c" if d == "bearish" else "#95a5a6" for d in directions]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=magnitudes, y=names,
        orientation="h",
        marker_color=colors,
        marker_line_width=0,
        hovertemplate="%{y}: %{x:.3f}<extra></extra>",
        text=[f"{m:.2f}" for m in magnitudes],
        textposition="outside",
        textfont={"color": "#bdc3c7", "size": 10},
    ))

    fig.update_layout(
        title={"text": title, "font": {"color": "#ecf0f1", "size": 13}, "x": 0.02},
        height=max(200, len(sectors) * 35),
        xaxis={"title": "Magnitude", "range": [0, 1.1]},
        yaxis={"autorange": "reversed"},
        **{k: v for k, v in DARK_TEMPLATE["layout"].items() if k not in ("margin", "xaxis", "yaxis")},
        margin={"l": 100, "r": 40, "t": 40, "b": 20},
        bargap=0.3,
    )
    fig.update_xaxes(tickfont={"size": 9, "color": "#95a5a6"}, title_font={"size": 10, "color": "#95a5a6"})
    fig.update_yaxes(tickfont={"size": 10, "color": "#bdc3c7"})

    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})


def market_prices_candlestick(
    data: List[Dict[str, Any]],
    ticker: str,
    title: Optional[str] = None,
) -> None:
    if not data:
        st.info(f"No market data for {ticker}.")
        return

    df = pd.DataFrame(data)
    date_col = next((c for c in ["date", "timestamp", "datetime"] if c in df.columns), None)
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col])

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.7, 0.3], vertical_spacing=0.04)

    o = df.get("open", df.get("open_price", []))
    h = df.get("high", df.get("high_price", []))
    lo = df.get("low", df.get("low_price", []))
    c = df.get("close", df.get("close_price", []))

    fig.add_trace(go.Candlestick(
        x=df[date_col] if date_col else df.index,
        open=o, high=h, low=lo, close=c,
        name=ticker,
        increasing_line_color="#2ecc71",
        decreasing_line_color="#e74c3c",
    ), row=1, col=1)

    returns = c.pct_change().dropna() * 100 if len(c) > 1 else []
    fig.add_trace(go.Bar(
        x=df[date_col].iloc[1:] if date_col and len(df) > 1 else df.index[1:],
        y=returns,
        name="Daily Return %",
        marker_color=["#2ecc71" if r >= 0 else "#e74c3c" for r in returns],
        opacity=0.7,
    ), row=2, col=1)

    fig.update_layout(
        title={"text": title or f"{ticker} Price Chart", "font": {"color": "#ecf0f1", "size": 13}, "x": 0.02},
        height=500,
        xaxis_rangeslider_visible=False,
        **{k: v for k, v in DARK_TEMPLATE["layout"].items() if k not in ("margin", "xaxis", "yaxis")},
        margin={"l": 40, "r": 20, "t": 40, "b": 30},
    )
    fig.update_xaxes(tickfont={"size": 9, "color": "#95a5a6"})
    fig.update_yaxes(tickfont={"size": 9, "color": "#95a5a6"})

    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})


def confidence_gauge(value: float, title: str = "Confidence") -> None:
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value * 100,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": title, "font": {"color": "#ecf0f1", "size": 14}},
        number={"font": {"color": "#ecf0f1", "size": 28}, "suffix": "%"},
        delta={"reference": 0.5, "position": "bottom",
               "increasing": {"color": "#2ecc71"},
               "decreasing": {"color": "#e74c3c"}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#95a5a6",
                     "tickfont": {"color": "#95a5a6", "size": 9}},
            "bar": {"color": "#3498db", "thickness": 0.6},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 30], "color": "rgba(231,76,60,0.15)"},
                {"range": [30, 60], "color": "rgba(241,196,15,0.15)"},
                {"range": [60, 100], "color": "rgba(46,204,113,0.15)"},
            ],
            "threshold": {
                "line": {"color": "#ecf0f1", "width": 2},
                "thickness": 0.8, "value": value * 100,
            },
        },
    ))
    fig.update_layout(
        height=200,
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#bdc3c7"},
        margin={"l": 20, "r": 20, "t": 30, "b": 10},
    )
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})


def volatility_gauge(vix_estimate: float, regime: str) -> None:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=min(vix_estimate, 60),
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": f"VIX Estimate ({regime.upper()})",
               "font": {"color": "#ecf0f1", "size": 13}},
        number={"font": {"color": "#ecf0f1", "size": 24}},
        gauge={
            "axis": {"range": [0, 60], "tickcolor": "#95a5a6",
                     "tickfont": {"color": "#95a5a6", "size": 9},
                     "tickvals": [0, 10, 20, 30, 40, 50, 60]},
            "bar": {"color": "#3498db", "thickness": 0.5},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 12], "color": "rgba(46,204,113,0.12)"},
                {"range": [12, 20], "color": "rgba(241,196,15,0.12)"},
                {"range": [20, 35], "color": "rgba(230,126,34,0.12)"},
                {"range": [35, 60], "color": "rgba(231,76,60,0.12)"},
            ],
            "threshold": {
                "line": {"color": "#ecf0f1", "width": 2},
                "thickness": 0.8, "value": min(vix_estimate, 60),
            },
        },
    ))
    fig.update_layout(height=180, paper_bgcolor="rgba(0,0,0,0)",
                      font={"color": "#bdc3c7"},
                      margin={"l": 20, "r": 20, "t": 30, "b": 10})
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})


def outcome_pie(outcomes: List[Dict[str, Any]]) -> None:
    if not outcomes:
        return
    labels = [o.get("scenario_label", "")[:20] for o in outcomes]
    values = [o.get("probability", 0) for o in outcomes]
    colors = ["#2ecc71", "#3498db", "#e74c3c", "#f1c40f", "#95a5a6"]

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        marker_colors=colors[:len(outcomes)],
        textinfo="label+percent",
        textfont={"color": "#ecf0f1", "size": 11},
        hole=0.4,
        hovertemplate="%{label}<br>%{percent}<extra></extra>",
        rotation=90,
        pull=[0.05 if i == 0 else 0 for i in range(len(outcomes))],
    ))
    fig.update_layout(
        title={"text": "Scenario Probabilities", "font": {"color": "#ecf0f1", "size": 13}, "x": 0.02},
        height=320,
        **{k: v for k, v in DARK_TEMPLATE["layout"].items() if k not in ("margin", "legend")},
        margin={"l": 20, "r": 20, "t": 40, "b": 10},
        showlegend=True,
        legend={"font": {"color": "#95a5a6", "size": 10}, "orientation": "h", "y": -0.2},
    )
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})


def return_comparison_bars(
    items: List[Dict[str, Any]],
    title: str = "Return Comparison (5d vs 30d)",
) -> None:
    if not items:
        return
    labels = [i.get("label", i.get("name", ""))[:10] for i in items]
    r5 = [i.get("return_5d", 0) for i in items]
    r30 = [i.get("return_30d", 0) for i in items]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="5d Return", x=labels, y=r5,
        marker_color="#5dade2", marker_line_width=0,
        hovertemplate="%{x}<br>5d: %{y:+.1f}%<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="30d Return", x=labels, y=r30,
        marker_color="#2e86c1", marker_line_width=0,
        hovertemplate="%{x}<br>30d: %{y:+.1f}%<extra></extra>",
    ))

    fig.update_layout(
        barmode="group",
        title={"text": title, "font": {"color": "#ecf0f1", "size": 13}, "x": 0.02},
        height=300,
        yaxis={"title": "Return (%)"},
        **{k: v for k, v in DARK_TEMPLATE["layout"].items() if k not in ("margin", "xaxis", "yaxis", "legend", "hovermode", "title", "height")},
        margin={"l": 40, "r": 20, "t": 40, "b": 40},
        legend={"font": {"color": "#95a5a6"}, "orientation": "h", "y": 1.08},
        hovermode="x",
    )
    fig.update_xaxes(tickfont={"size": 9, "color": "#bdc3c7"})
    fig.update_yaxes(tickfont={"size": 9, "color": "#95a5a6"})

    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})


def signal_contribution_waterfall(signals: Dict[str, float]) -> None:
    if not signals:
        return
    labels = list(signals.keys())
    values = list(signals.values())
    colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in values]

    fig = go.Figure(go.Waterfall(
        name="", orientation="v",
        measure=["relative"] * len(labels),
        x=[l.replace("_", " ").title() for l in labels],
        y=values,
        text=[f"{v:+.3f}" for v in values],
        textposition="outside",
        textfont={"color": "#bdc3c7", "size": 10},
        connector={"line": {"color": "rgba(255,255,255,0.1)", "width": 1}},
        increasing={"marker": {"color": "#2ecc71"}},
        decreasing={"marker": {"color": "#e74c3c"}},
    ))
    fig.update_layout(
        title={"text": "Signal Decomposition", "font": {"color": "#ecf0f1", "size": 13}, "x": 0.02},
        height=300,
        **{k: v for k, v in DARK_TEMPLATE["layout"].items() if k not in ("margin", "xaxis", "yaxis", "hovermode", "title", "height")},
        margin={"l": 40, "r": 20, "t": 40, "b": 40},
        hovermode="x",
        showlegend=False,
    )
    fig.update_xaxes(tickfont={"size": 9, "color": "#bdc3c7"})
    fig.update_yaxes(tickfont={"size": 9, "color": "#95a5a6"})

    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})


def plot_bar_chart(
    labels: List[str],
    values: List[float],
    title: str = "",
    colors: Optional[List[str]] = None,
) -> None:
    if not labels or not values:
        st.info("No data to plot.")
        return
    if colors is None:
        colors = ["#3498db"] * len(labels)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=values, y=labels,
        orientation="h",
        marker_color=colors[:len(labels)],
        marker_line_width=0,
        hovertemplate="%{y}: %{x:.3f}<extra></extra>",
        text=[f"{v:.2f}" for v in values],
        textposition="outside",
        textfont={"color": "#bdc3c7", "size": 10},
    ))
    fig.update_layout(
        title={"text": title, "font": {"color": "#ecf0f1", "size": 13}, "x": 0.02},
        height=max(200, len(labels) * 35),
        xaxis={"title": "", "range": [0, max(values or [1]) * 1.15 if values else 1]},
        yaxis={"autorange": "reversed"},
        **{k: v for k, v in DARK_TEMPLATE["layout"].items() if k not in ("margin", "xaxis", "yaxis")},
        margin={"l": 120, "r": 40, "t": 40, "b": 20},
        bargap=0.3,
    )
    fig.update_xaxes(tickfont={"size": 9, "color": "#95a5a6"})
    fig.update_yaxes(tickfont={"size": 10, "color": "#bdc3c7"})
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})


def plot_impact_heatmap(
    sectors: List[str],
    scores: List[float],
    title: str = "Sector Impact Matrix",
) -> None:
    if not sectors or not scores:
        st.info("No sector impact data.")
        return
    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        z=[scores],
        x=sectors,
        y=["Impact"],
        colorscale=[
            [0.0, "#8b0000"], [0.25, "#e74c3c"], [0.45, "#7f8c8d"],
            [0.55, "#7f8c8d"], [0.75, "#2ecc71"], [1.0, "#006400"],
        ],
        zmin=-1, zmax=1,
        text=[[f"{s:.2f}" for s in scores]],
        texttemplate="%{text}",
        textfont={"size": 12, "color": "#ecf0f1"},
        showscale=True,
        colorbar={"title": {"text": "Impact", "font": {"color": "#95a5a6", "size": 10}},
                   "tickfont": {"color": "#95a5a6", "size": 9}, "len": 0.6, "thickness": 12},
    ))
    fig.update_layout(
        title={"text": title, "font": {"color": "#ecf0f1", "size": 13}, "x": 0.02},
        height=160,
        **{k: v for k, v in DARK_TEMPLATE["layout"].items() if k not in ("margin", "xaxis", "yaxis")},
        margin={"l": 10, "r": 60, "t": 40, "b": 10},
        xaxis={"side": "bottom", "tickangle": -30},
        yaxis={"visible": False},
    )
    fig.update_xaxes(tickfont={"size": 10, "color": "#bdc3c7"})
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})




def plot_market_prices(data: List[Dict[str, Any]], ticker: str) -> None:
    market_prices_candlestick(data, ticker)


def plot_gauge(value: float, title: str = "Confidence") -> None:
    confidence_gauge(value, title)


def plot_pie_chart(
    labels: List[str], values: List[float], title: str = "",
) -> None:
    if not labels or not values:
        return
    colors_pie = ["#2ecc71", "#3498db", "#e74c3c", "#f1c40f", "#95a5a6", "#9b59b6", "#1abc9c", "#e67e22"]
    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        marker_colors=colors_pie[:len(labels)],
        textinfo="label+percent",
        textfont={"color": "#ecf0f1", "size": 11},
        hole=0.4,
        hovertemplate="%{label}<br>%{percent}<extra></extra>",
        rotation=90,
    ))
    fig.update_layout(
        title={"text": title, "font": {"color": "#ecf0f1", "size": 13}, "x": 0.02},
        height=280,
        **{k: v for k, v in DARK_TEMPLATE["layout"].items() if k not in ("margin", "legend")},
        margin={"l": 20, "r": 20, "t": 40, "b": 10},
        showlegend=True,
        legend={"font": {"color": "#95a5a6", "size": 10}, "orientation": "h", "y": -0.2},
    )
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})


def plot_sentiment_timeline(
    data_points: List[Dict[str, Any]], title: str = "Sentiment Over Time",
) -> None:
    sentiment_timeline(data_points, title)


def sentiment_timeline(
    data_points: List[Dict[str, Any]],
    title: str = "Sentiment & Volume Over Time",
) -> None:
    if not data_points:
        st.info("No sentiment data.")
        return

    df = pd.DataFrame(data_points)
    ts_col = next((c for c in ["timestamp", "date", "created_utc"] if c in df.columns), None)
    if ts_col:
        df[ts_col] = pd.to_datetime(df[ts_col])

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        x=df[ts_col] if ts_col else df.index,
        y=df.get("score", df.get("sentiment", [])),
        mode="lines+markers",
        name="Sentiment",
        line={"color": "#3498db", "width": 2},
        marker={"size": 4, "color": "#3498db"},
        hovertemplate="%{x}<br>Sentiment: %{y:.3f}<extra></extra>",
    ), secondary_y=False)
    vol = df.get("volume", df.get("num_comments", df.get("mention_count", [])))
    fig.add_trace(go.Bar(
        x=df[ts_col] if ts_col else df.index,
        y=vol,
        name="Volume",
        marker={"color": "rgba(149,165,166,0.3)"},
        hovertemplate="Volume: %{y}<extra></extra>",
    ), secondary_y=True)

    fig.update_layout(
        title={"text": title, "font": {"color": "#ecf0f1", "size": 13}, "x": 0.02},
        height=300,
        **{k: v for k, v in DARK_TEMPLATE["layout"].items() if k not in ("margin", "xaxis", "yaxis")},
        margin={"l": 40, "r": 40, "t": 40, "b": 30},
        legend={"font": {"color": "#95a5a6"}, "orientation": "h", "y": 1.08},
    )
    fig.update_xaxes(tickfont={"size": 9, "color": "#95a5a6"})
    fig.update_yaxes(tickfont={"size": 9, "color": "#95a5a6"}, secondary_y=False)
    fig.update_yaxes(tickfont={"size": 9, "color": "#95a5a6"}, secondary_y=True)

    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
