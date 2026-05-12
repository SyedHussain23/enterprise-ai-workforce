"""
Structured JSON logger with request correlation.

Why JSON logs:
- Grep-able by any field (request_id, agent, department, user_id)
- Works out-of-the-box with Datadog, CloudWatch, Loki, Papertrail
- Preserves structure — no regex parsing needed
- Adds request_id threading so you can trace a full workflow in one filter

Usage:
    from app.core.logger import get_logger
    logger = get_logger(__name__)
    logger.info("agent.classified", department="HR", confidence=85)

    # Request-scoped — set at request entry, auto-included in all logs
    from app.core.logger import set_request_id, clear_request_id
"""
import json
import logging
import os
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings

# ── Request ID context var ────────────────────────────────────────────────────
# ContextVar is async-safe — each request coroutine gets its own slot
_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def set_request_id(request_id: str) -> None:
    _request_id_var.set(request_id)


def get_request_id() -> str | None:
    return _request_id_var.get()


def clear_request_id() -> None:
    _request_id_var.set(None)


# ── JSON log formatter ────────────────────────────────────────────────────────
class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        rid = get_request_id()
        if rid:
            log["request_id"] = rid

        # Extra fields set via logger.info("msg", extra={...})
        for key, val in record.__dict__.items():
            if key not in (
                "args", "asctime", "created", "exc_info", "exc_text",
                "filename", "funcName", "id", "levelname", "levelno",
                "lineno", "message", "module", "msecs", "msg", "name",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "thread", "threadName", "taskName",
            ):
                log[key] = val

        if record.exc_info:
            log["exception"] = self.formatException(record.exc_info)

        return json.dumps(log, default=str)


# ── Logger factory ────────────────────────────────────────────────────────────
_configured = False


def _configure_root_logger() -> None:
    global _configured
    if _configured:
        return
    _configured = True

    os.makedirs("logs", exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    # Console handler — always JSON in production, human-friendly in DEBUG
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(JSONFormatter())
    root.addHandler(console)

    # File handler
    file_handler = logging.FileHandler("logs/app.log")
    file_handler.setFormatter(JSONFormatter())
    root.addHandler(file_handler)

    # Silence noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)


class AppLogger:
    """
    Thin wrapper around stdlib Logger that accepts keyword arguments directly.

    Standard logging requires extra={"key": val}.
    This wrapper lets us write logger.info("msg", department="HR", confidence=85)
    and packs kwargs into the extra dict automatically.
    """

    def __init__(self, name: str) -> None:
        _configure_root_logger()
        self._log = logging.getLogger(name)

    def _emit(self, level: int, msg: str, **kwargs: Any) -> None:
        self._log.log(level, msg, extra=kwargs, stacklevel=3)

    def debug(self, msg: str, **kwargs: Any) -> None:
        self._emit(logging.DEBUG, msg, **kwargs)

    def info(self, msg: str, **kwargs: Any) -> None:
        self._emit(logging.INFO, msg, **kwargs)

    def warning(self, msg: str, **kwargs: Any) -> None:
        self._emit(logging.WARNING, msg, **kwargs)

    def error(self, msg: str, **kwargs: Any) -> None:
        self._emit(logging.ERROR, msg, **kwargs)

    def exception(self, msg: str, **kwargs: Any) -> None:
        self._log.exception(msg, extra=kwargs, stacklevel=2)


def get_logger(name: str) -> AppLogger:
    return AppLogger(name)


# Module-level convenience logger
logger = get_logger(__name__)
