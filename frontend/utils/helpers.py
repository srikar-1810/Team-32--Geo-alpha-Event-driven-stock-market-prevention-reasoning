from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


def format_timestamp(dt_str: Optional[str]) -> str:
    if not dt_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except (ValueError, AttributeError):
        return str(dt_str)[:19]


def format_percentage(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"{value:+.2%}" if abs(value) > 0.01 else f"{value:.2%}"


def format_currency(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"${value:,.2f}"


def format_number(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.2f}K"
    return f"{value:,.2f}"


def severity_color(severity: float) -> str:
    if severity >= 0.7:
        return "red"
    if severity >= 0.4:
        return "orange"
    return "green"


def sentiment_color(score: float) -> str:
    if score > 0.2:
        return "green"
    if score < -0.2:
        return "red"
    return "gray"


def status_color(status: str) -> str:
    status_map = {
        "healthy": "green",
        "completed": "green",
        "running": "blue",
        "failed": "red",
        "error": "red",
        "pending": "gray",
        "idle": "gray",
        "degraded": "orange",
        "warning": "orange",
    }
    return status_map.get(status.lower(), "gray")


def truncate(text: str, max_length: int = 100) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def parse_date_range(preset: str) -> tuple:
    today = datetime.utcnow()
    presets = {
        "24h": today - timedelta(hours=24),
        "7d": today - timedelta(days=7),
        "30d": today - timedelta(days=30),
        "90d": today - timedelta(days=90),
        "1y": today - timedelta(days=365),
    }
    return presets.get(preset, today - timedelta(days=7)), today
