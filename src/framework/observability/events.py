"""Structured, correlated application events."""

import logging
from datetime import UTC, datetime
from typing import Any

from src.framework.observability.correlation import current_correlation_context
from src.framework.observability.redaction import redact_fields

_LOGGER = logging.getLogger("tillegal.observability")


def log_event(
    event: str,
    *,
    component: str,
    level: int = logging.INFO,
    **fields: Any,
) -> None:
    """Emit one structured event without logging sensitive payload fields."""
    event_data: dict[str, object] = {
        **redact_fields(fields),
        "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "level": logging.getLevelName(level),
        "event": event,
        "component": component,
        **current_correlation_context(),
    }
    _LOGGER.log(level, event, extra={"event_data": event_data})
