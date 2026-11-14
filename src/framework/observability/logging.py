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
            for key in ("crawl_job_id", "crawl_date", "error_category", "error_message"):
                value = getattr(record, key, None)
                if value is not None:
                    payload[key] = value
            if record.exc_info is not None:
                error = record.exc_info[1]
                if error is not None:
                    payload["exception"] = f"{type(error).__name__}: {error}"
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
