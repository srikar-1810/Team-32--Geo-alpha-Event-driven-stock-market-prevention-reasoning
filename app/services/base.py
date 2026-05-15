from __future__ import annotations

from typing import Any, Dict, Generic, Optional, TypeVar

from tenacity import (
    after_log,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tenacity.stop import stop_never

from app.config import settings
from app.logging_config import get_logger

T = TypeVar("T")
logger = get_logger(__name__)


def default_retry(
    max_attempts: int = 3,
    min_wait: int = 1,
    max_wait: int = 30,
    exceptions=(Exception,),
):
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        after=after_log(logger, 20),
        before_sleep=before_sleep_log(logger, 20),
        reraise=True,
    )


class BaseService:
    """Base class for all services with common utilities."""

    def __init__(self, service_name: str) -> None:
        self.service_name = service_name
        self.logger = get_logger(f"services.{service_name}")

    def validate_config(self, required_keys: list[str]) -> None:
        missing = [k for k in required_keys if not getattr(settings, k, None)]
        if missing:
            raise ValueError(
                f"{self.service_name}: missing required config: {', '.join(missing)}"
            )
