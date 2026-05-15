from __future__ import annotations

import os
from typing import Optional

from pydantic_settings import BaseSettings


class FrontendSettings(BaseSettings):
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")
    APP_NAME: str = "GeoMarketGPT"
    APP_VERSION: str = "0.1.0"
    POLL_INTERVAL: int = 30
    MAX_CHART_POINTS: int = 500
    ENABLE_REFRESH: bool = True
    MOCK_MODE: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = FrontendSettings()
