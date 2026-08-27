"""
app/core/logging.py — Structured logging configuration.

Outputs JSON in production, human-readable text in development.
Every log record includes: request_id, timestamp, level, module, message.
"""
from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Context variable to propagate request IDs across async tasks
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def generate_request_id() -> str:
    return str(uuid.uuid4())


class JsonFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects."""

    SENSITIVE_KEYS = frozenset({
        "password", "token", "secret", "key", "authorization",
        "auth_token", "private_key", "encryption_key", "medical",
    })

    def format(self, record: logging.LogRecord) -> str:
        import json

        data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        req_id = request_id_var.get("")
        if req_id:
            data["request_id"] = req_id

        # Attach extra fields, but scrub sensitive keys
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in {
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
                "taskName",
            }:
                continue
            if any(s in key.lower() for s in self.SENSITIVE_KEYS):
                data[key] = "***REDACTED***"
            else:
                data[key] = value

        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)

        return json.dumps(data, default=str)


class TextFormatter(logging.Formatter):
    """Human-readable formatter for development."""

    FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
    DATEFMT = "%Y-%m-%d %H:%M:%S"

    def __init__(self) -> None:
        super().__init__(fmt=self.FORMAT, datefmt=self.DATEFMT)


def configure_logging(level: str = "INFO", fmt: str = "json") -> None:
    """
    Configure the root logger.

    Args:
        level: Log level string (e.g. "INFO", "DEBUG").
        fmt: "json" for structured JSON, "text" for human-readable.
    """
    numeric_level = logging.getLevelName(level.upper())

    formatter: logging.Formatter
    if fmt.lower() == "json":
        formatter = JsonFormatter()
    else:
        formatter = TextFormatter()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Reduce noise from third-party libraries
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger("uvicorn.error").setLevel(numeric_level)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Use module __name__ as the name."""
    return logging.getLogger(name)
