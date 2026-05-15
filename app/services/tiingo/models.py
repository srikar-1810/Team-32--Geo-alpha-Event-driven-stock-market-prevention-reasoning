from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TiingoPriceQuery(BaseModel):
    ticker: str
    start_date: date
    end_date: date
    frequency: str = "daily"


class TiingoPriceResponse(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    adj_open: Optional[float] = None
    adj_high: Optional[float] = None
    adj_low: Optional[float] = None
    adj_close: Optional[float] = None
    adj_volume: Optional[int] = None
    div_cash: Optional[float] = None
    split_factor: Optional[float] = None


class TiingoMetadata(BaseModel):
    ticker: str
    name: str
    exchange: str = ""
    asset_type: str = "Stock"
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class TiingoNewsArticle(BaseModel):
    id: int
    title: str
    description: str
    source: str
    url: str
    published_date: datetime
    tickers: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)


class TiingoIEXData(BaseModel):
    ticker: str
    timestamp: Optional[datetime] = None
    last_sale_price: Optional[float] = None
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    volume: Optional[int] = None
    prev_close: Optional[float] = None
