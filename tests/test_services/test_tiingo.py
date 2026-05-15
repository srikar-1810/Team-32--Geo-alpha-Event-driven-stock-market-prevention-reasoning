from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from app.services.tiingo.client import TiingoClient
from app.services.tiingo.models import TiingoPriceResponse


class TestTiingoModels:
    def test_price_response_model(self):
        data = TiingoPriceResponse(
            date="2024-01-01",
            open=150.0,
            high=155.0,
            low=149.0,
            close=154.0,
            volume=10000000,
        )
        assert data.open == 150.0
        assert data.close == 154.0

    def test_price_response_with_adjustments(self):
        data = TiingoPriceResponse(
            date="2024-01-01",
            open=150.0,
            high=155.0,
            low=149.0,
            close=154.0,
            volume=10000000,
            adj_close=152.0,
            div_cash=0.5,
        )
        assert data.adj_close == 152.0
        assert data.div_cash == 0.5
