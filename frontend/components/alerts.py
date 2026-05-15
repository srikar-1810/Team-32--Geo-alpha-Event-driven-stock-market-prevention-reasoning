from __future__ import annotations

from typing import Any, Dict, List, Optional

import streamlit as st


def show_success(message: str, duration: int = 3) -> None:
    st.success(message, icon="✅")


def show_error(message: str, details: Optional[str] = None) -> None:
    msg = message
    if details:
        msg += f"\n\n{details}"
    st.error(msg, icon="❌")


def show_warning(message: str, details: Optional[str] = None) -> None:
    msg = message
    if details:
        msg += f"\n\n{details}"
    st.warning(msg, icon="⚠️")


def show_info(message: str) -> None:
    st.info(message, icon="ℹ️")


def show_metric_alert(
    label: str,
    value: float,
    threshold: float,
    direction: str = "above",
) -> None:
    triggered = (value > threshold) if direction == "above" else (value < threshold)
    if triggered:
        st.warning(
            f"⚠️ **{label}**: {value:.2f} has crossed threshold {threshold:.2f} ({direction})",
            icon="⚠️",
        )
