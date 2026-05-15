from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Optional


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def today() -> date:
    return utc_now().date()


def parse_iso_date(date_str: str) -> Optional[date]:
    try:
        return datetime.fromisoformat(date_str).date()
    except (ValueError, TypeError):
        return None


def parse_iso_datetime(date_str: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None


def date_range(start: date, end: date) -> list[date]:
    delta = (end - start).days
    return [start + timedelta(days=i) for i in range(delta + 1)]


def hours_ago(hours: int) -> datetime:
    return utc_now() - timedelta(hours=hours)


def days_ago(days: int) -> datetime:
    return utc_now() - timedelta(days=days)


def format_event_date(dt: Optional[datetime]) -> str:
    if dt is None:
        return "Unknown"
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def get_fiscal_quarter(d: Optional[date] = None) -> str:
    d = d or today()
    quarter = (d.month - 1) // 3 + 1
    return f"Q{quarter} {d.year}"


def is_market_open(dt: Optional[datetime] = None) -> bool:
    dt = dt or utc_now()
    if dt.weekday() >= 5:
        return False
    est = dt - timedelta(hours=5)
    return 9 <= est.hour < 16


def next_market_open(dt: Optional[datetime] = None) -> datetime:
    dt = dt or utc_now()
    while dt.weekday() >= 5:
        dt += timedelta(days=1)
    est = dt - timedelta(hours=5)
    next_open = est.replace(hour=9, minute=30, second=0, microsecond=0)
    if next_open <= est:
        next_open += timedelta(days=1)
    while next_open.weekday() >= 5:
        next_open += timedelta(days=1)
    return next_open + timedelta(hours=5)
