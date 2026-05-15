from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Dict, Optional

import structlog

from app.config import settings


LOG_DIR = Path(settings.ROOT_DIR) / "logs"
LOG_DIR.mkdir(exist_ok=True)


def _add_app_context(logger: logging.Logger, method_name: str, event_dict: Dict) -> Dict:
    event_dict["app"] = settings.APP_NAME
    event_dict["version"] = settings.APP_VERSION
    event_dict["env"] = settings.APP_ENV.value
    return event_dict


def _add_timestamp(logger: logging.Logger, method_name: str, event_dict: Dict) -> Dict:
    import datetime
    event_dict["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
    return event_dict


def setup_logging() -> None:
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.DEBUG)

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            _add_app_context,
            structlog.dev.ConsoleRenderer()
            if settings.is_development
            else structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer()
        if settings.is_development
        else structlog.processors.JSONRenderer(),
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    file_handler = logging.FileHandler(LOG_DIR / "geomarketgpt.log")
    file_handler.setLevel(log_level)
    file_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    error_file_handler = logging.FileHandler(LOG_DIR / "error.log")
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_file_handler)

    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers.clear()
    uvicorn_logger.propagate = True

    for lib_logger in ("httpx", "httpcore", "urllib3", "asyncio"):
        logging.getLogger(lib_logger).setLevel(logging.WARNING)


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name or __name__)
