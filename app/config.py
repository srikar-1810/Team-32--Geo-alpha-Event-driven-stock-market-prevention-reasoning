from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────
    APP_NAME: str = "GeoMarketGPT"
    APP_VERSION: str = "0.1.0"
    APP_ENV: AppEnvironment = AppEnvironment.DEVELOPMENT
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-to-a-random-secret"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "DEBUG"

    # ── Database ───────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://geogpt:geogpt@localhost:5432/geomarket_gpt"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # ── Redis ──────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50

    # ── ChromaDB ───────────────────────────
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    CHROMA_COLLECTION_EVENTS: str = "geopol_events"
    CHROMA_COLLECTION_SENTIMENT: str = "sentiment_data"
    CHROMA_COLLECTION_MARKETS: str = "market_data"
    CHROMA_COLLECTION_REPORTS: str = "reports"
    CHROMA_COLLECTION_HISTORICAL: str = "historical_events"
    CHROMA_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHROMA_EMBEDDING_CACHE_SIZE: int = 10000
    CHROMA_EMBEDDING_CACHE_PATH: str = "data/cache/embeddings.json"
    HISTORICAL_RAG_TOP_K_DEFAULT: int = 10
    HISTORICAL_RAG_MAX_CONTEXT_CHARS: int = 8000
    HISTORICAL_RAG_MIN_SIMILARITY: float = 0.3
    HISTORICAL_RAG_CONFIDENCE_THRESHOLD: float = 0.4

    # ── GDELT ──────────────────────────────
    GDELT_BASE_URL: str = "https://api.gdeltproject.org/api/v2"
    GDELT_TIMEOUT: int = 30
    GDELT_MAX_RETRIES: int = 3
    GDELT_POLL_INTERVAL: int = 1200
    GDELT_QUERIES: str = "conflict,war,sanctions,election,crisis,protest,military,trade,terrorism,diplomacy,oil,inflation,interest rates,central bank,tariff,treaty,summit,weapon,nuclear,cyberattack"

    @property
    def gdelt_queries_list(self) -> List[str]:
        return [q.strip() for q in self.GDELT_QUERIES.split(",") if q.strip()]

    # ── Reddit ─────────────────────────────
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None
    REDDIT_USER_AGENT: str = "GeoMarketGPT/0.1.0"
    REDDIT_SUBREDDITS: str = "wallstreetbets,stocks,investing,geopolitics,worldnews,economics,StockMarket,options,MarketSentiment,trade"
    REDDIT_FETCH_LIMIT: int = 100
    REDDIT_POLL_INTERVAL: int = 300
    REDDIT_CONCURRENCY: int = 3
    REDDIT_SORT_STRATEGY: str = "balanced"
    REDDIT_MAX_POST_AGE_HOURS: int = 24

    @property
    def reddit_subreddits_list(self) -> List[str]:
        return [s.strip() for s in self.REDDIT_SUBREDDITS.split(",") if s.strip()]

    # ── Tiingo ─────────────────────────────
    TIINGO_API_TOKEN: Optional[str] = None
    TIINGO_BASE_URL: str = "https://api.tiingo.com"
    TIINGO_TIMEOUT: int = 30
    TIINGO_MAX_RETRIES: int = 3
    TIINGO_RATE_LIMIT: int = 500
    TIINGO_SECTOR_ETFS: str = "SPY,QQQ,IWM,EEM,XLF,XLE,XLK,XLV,XLI,XLB,XLU,XLY,XLP,XLRE,XLC,VNQ,GLD,SLV,USO,TLT,SHY,AGG,LQD,HYG"

    @property
    def tiingo_sector_etfs_list(self) -> List[str]:
        return [s.strip() for s in self.TIINGO_SECTOR_ETFS.split(",") if s.strip()]

    # ── Yahoo Finance ──────────────────────
    YAHOO_ENABLE_FALLBACK: bool = True
    YAHOO_TIMEOUT: int = 30

    # ── Ingestion ──────────────────────────
    INGESTION_CACHE_TTL_HOURS: int = 24
    INGESTION_MARKET_HOURS_ONLY: bool = True

    # ── LLM Provider ───────────────────────
    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4-turbo"
    OPENAI_BASE_URL: Optional[str] = None
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_MAX_TOKENS: int = 4096
    OPENAI_TEMPERATURE: float = 0.2
    XAI_API_KEY: Optional[str] = None
    XAI_MODEL: str = "grok-2-latest"
    XAI_BASE_URL: str = "https://api.x.ai/v1"

    @property
    def llm_api_key(self) -> Optional[str]:
        if self.LLM_PROVIDER == "xai":
            return self.XAI_API_KEY
        return self.OPENAI_API_KEY

    @property
    def llm_model(self) -> str:
        if self.LLM_PROVIDER == "xai":
            return self.XAI_MODEL
        return self.OPENAI_MODEL

    @property
    def llm_base_url(self) -> Optional[str]:
        if self.LLM_PROVIDER == "xai":
            return self.XAI_BASE_URL
        return self.OPENAI_BASE_URL

    # ── Reports / Autonomous Brief ──────────
    REPORT_AUTO_GENERATE_INTERVAL: int = 1200
    REPORT_KEEP_HOURS: int = 72
    REPORT_OUTPUT_DIR: str = "data/reports"
    REPORT_MAX_EVENTS_PER_BRIEF: int = 15
    REPORT_MAX_SECTORS_PER_BRIEF: int = 10

    # ── LangChain ──────────────────────────
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str = "GeoMarketGPT"

    # ── Celery ─────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: List[str] = ["json"]

    # ── Monitoring ─────────────────────────
    SENTRY_DSN: Optional[str] = None
    PROMETHEUS_PORT: int = 9090
    ENABLE_METRICS: bool = True

    # ── Derived ────────────────────────────
    ROOT_DIR: Path = Path(__file__).resolve().parent.parent

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == AppEnvironment.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == AppEnvironment.PRODUCTION

    @property
    def sync_database_url(self) -> str:
        return self.DATABASE_URL.replace("+asyncpg", "")

    @property
    def chroma_url(self) -> str:
        return f"http://{self.CHROMA_HOST}:{self.CHROMA_PORT}"


settings = Settings()
