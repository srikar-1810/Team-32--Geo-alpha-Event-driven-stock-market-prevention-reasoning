from __future__ import annotations

from typing import Any, Dict, Optional


class GeoMarketGPTException(Exception):
    """Base exception for all GeoMarketGPT errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ServiceException(GeoMarketGPTException):
    """Raised when an external service fails."""

    def __init__(self, service: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=f"[{service}] {message}",
            error_code="SERVICE_ERROR",
            status_code=502,
            details=details,
        )


class ConfigurationException(GeoMarketGPTException):
    """Raised when required configuration is missing or invalid."""

    def __init__(self, key: str, message: Optional[str] = None) -> None:
        super().__init__(
            message=message or f"Missing or invalid configuration: {key}",
            error_code="CONFIG_ERROR",
            status_code=500,
        )


class ValidationException(GeoMarketGPTException):
    """Raised on input validation failures."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            details=details,
        )


class NotFoundException(GeoMarketGPTException):
    """Raised when a requested resource is not found."""

    def __init__(self, resource: str, identifier: Optional[str] = None) -> None:
        msg = f"{resource} not found"
        if identifier:
            msg += f": {identifier}"
        super().__init__(
            message=msg,
            error_code="NOT_FOUND",
            status_code=404,
        )


class RateLimitException(GeoMarketGPTException):
    """Raised when rate limit is exceeded."""

    def __init__(self, service: str, retry_after: int = 60) -> None:
        super().__init__(
            message=f"Rate limit exceeded for {service}. Retry after {retry_after}s.",
            error_code="RATE_LIMIT",
            status_code=429,
            details={"retry_after": retry_after, "service": service},
        )


class AgentException(GeoMarketGPTException):
    """Raised when an AI agent encounters an error."""

    def __init__(self, agent: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=f"[Agent:{agent}] {message}",
            error_code="AGENT_ERROR",
            status_code=500,
            details=details,
        )
