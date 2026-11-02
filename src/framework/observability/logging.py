"""Logging setup for the service."""

import json
import logging
from datetime import UTC, datetime
from typing import Any


class JsonLogFormatter(logging.Formatter):
    """Format log records as JSON for local logs and log collectors."""

    def format(self, record: logging.LogRecord) -> str:
        event_data = getattr(record, "event_data", None)
        if isinstance(event_data, dict):
            payload: dict[str, Any] = event_data
        else:
            payload = {
                "timestamp": datetime.fromtimestamp(record.created, UTC)
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z"),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
        return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))


def configure_logging(level: str) -> None:
    """Configure root logging to emit JSON while preserving existing handlers."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    if not root_logger.handlers:
        root_logger.addHandler(logging.StreamHandler())
    formatter = JsonLogFormatter()
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)
