from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.observability.context import get_method, get_path, get_request_id, get_user_id

_LOGGING_CONFIGURED = False

# Skip std fields.
_RESERVED_LOG_RECORD_FIELDS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
    "asctime",
}


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Fill missing ctx.
        if not getattr(record, "request_id", None):
            record.request_id = get_request_id()
        if not getattr(record, "user_id", None):
            record.user_id = get_user_id()
        if not getattr(record, "path", None):
            record.path = get_path()
        if not getattr(record, "method", None):
            record.method = get_method()
        return True


class JsonLogFormatter(logging.Formatter):
    def __init__(self, service_name: str, environment: str) -> None:
        super().__init__()
        self.service_name = service_name
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        # Base JSON log.
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service_name": self.service_name,
            "environment": self.environment,
        }

        for key in ("request_id", "user_id", "path", "method", "status_code", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value

        if record.exc_info:
            exc_type = record.exc_info[0]
            exc_value = record.exc_info[1]
            payload["exception_type"] = exc_type.__name__ if exc_type else None
            payload["exception_message"] = str(exc_value) if exc_value else None

        # Keep custom extras.
        for key, value in record.__dict__.items():
            if key in _RESERVED_LOG_RECORD_FIELDS:
                continue
            if key.startswith("_"):
                continue
            if key in payload:
                continue
            payload[key] = value

        return json.dumps(payload, ensure_ascii=False, default=str)


def _build_stream_handler(service_name: str, environment: str) -> logging.Handler:
    # Stdout logs.
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter(service_name=service_name, environment=environment))
    handler.addFilter(RequestContextFilter())
    return handler


def _build_file_handler(service_name: str, environment: str, file_path: str) -> logging.Handler:
    # File logs.
    directory = os.path.dirname(file_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    handler = logging.FileHandler(file_path, encoding="utf-8")
    handler.setFormatter(JsonLogFormatter(service_name=service_name, environment=environment))
    handler.addFilter(RequestContextFilter())
    return handler


def setup_logging(*, service_name: str | None = None) -> None:
    global _LOGGING_CONFIGURED

    # Run once.
    if _LOGGING_CONFIGURED:
        return

    resolved_service_name = service_name or settings.SERVICE_NAME
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)
    root_logger.addHandler(
        _build_stream_handler(
            service_name=resolved_service_name,
            environment=settings.APP_ENV,
        )
    )

    log_file_path = settings.LOG_FILE_PATH.strip()
    if log_file_path:
        root_logger.addHandler(
            _build_file_handler(
                service_name=resolved_service_name,
                environment=settings.APP_ENV,
                file_path=log_file_path,
            )
        )

    for logger_name in (
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "fastapi",
        "celery",
        "kombu",
    ):
        # Reuse root handlers.
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True
        logger.setLevel(level)

    _LOGGING_CONFIGURED = True
