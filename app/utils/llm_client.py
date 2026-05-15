from __future__ import annotations

from typing import Optional

from openai import AsyncOpenAI

from app.config import settings


def create_llm_client() -> AsyncOpenAI:
    kwargs = {"api_key": settings.llm_api_key}
    base_url = settings.llm_base_url
    if base_url:
        kwargs["base_url"] = base_url
    return AsyncOpenAI(**kwargs)
