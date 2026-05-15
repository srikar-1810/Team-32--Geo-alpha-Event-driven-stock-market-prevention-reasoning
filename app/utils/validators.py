from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

TICKER_PATTERN = re.compile(r"^[A-Z]{1,5}$")
TICKER_LIST_PATTERN = re.compile(r"^[A-Z]{1,5}(,[A-Z]{1,5})*$")
URL_PATTERN = re.compile(r"^https?://[^\s/$.?#].[^\s]*$")
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
CRON_PATTERN = re.compile(
    r"^(\*|([0-5]?\d))\s"
    r"(\*|([01]?\d|2[0-3]))\s"
    r"(\*|([01]?\d|2[0-3]))\s"
    r"(\*|([01]?\d|2[0-3]))\s"
    r"(\*|([0-6]))$"
)


def validate_ticker(ticker: str) -> bool:
    return bool(TICKER_PATTERN.match(ticker.strip().upper()))


def validate_ticker_list(tickers: str) -> List[str]:
    tickers = tickers.strip().upper()
    if not TICKER_LIST_PATTERN.match(tickers):
        raise ValueError(f"Invalid ticker list format: {tickers}")
    return [t.strip() for t in tickers.split(",") if t.strip()]


def validate_url(url: str) -> bool:
    return bool(URL_PATTERN.match(url))


def validate_email(email: str) -> bool:
    return bool(EMAIL_PATTERN.match(email))


def validate_cron(expression: str) -> bool:
    return bool(CRON_PATTERN.match(expression))


def validate_severity(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def validate_sentiment_score(value: float) -> float:
    return max(-1.0, min(1.0, float(value)))


def validate_confidence(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def sanitize_query(query: str, max_length: int = 2000) -> str:
    cleaned = query.strip()[:max_length]
    return cleaned
