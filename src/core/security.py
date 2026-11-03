"""Security helpers shared by application and infrastructure code."""

import re
from collections.abc import Mapping

from src.core.constants import REDACTED_VALUE

_SENSITIVE_FIELD_NAMES = {
    "answer",
    "anon_key",
    "authorization",
    "body",
    "connection_string",
    "content",
    "credential",
    "database_url",
    "document",
    "embedding",
    "headers",
    "message",
    "messages",
    "password",
    "private_key",
    "prompt",
    "query",
    "response",
    "request",
    "secret",
    "service_role_key",
    "token",
}
_SENSITIVE_FIELD_PARTS = (
    "access_token",
    "anon_key",
    "api_key",
    "authorization",
    "body",
    "connection_string",
    "content",
    "credential",
    "database_url",
    "document",
    "embedding",
    "header",
    "message",
    "password",
    "private_key",
    "prompt",
    "query",
    "refresh_token",
    "secret",
    "service_role_key",
)


def redact_fields(fields: Mapping[str, object]) -> dict[str, object]:
    """Return a JSON-safe copy with sensitive fields redacted."""
    return {key: _redact_value(key, value) for key, value in fields.items()}


def _redact_value(key: str, value: object) -> object:
    normalized_key = re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")
    if normalized_key in _SENSITIVE_FIELD_NAMES or any(
        part in normalized_key for part in _SENSITIVE_FIELD_PARTS
    ):
        return REDACTED_VALUE
    if isinstance(value, Mapping):
        return redact_fields({str(nested_key): nested_value for nested_key, nested_value in value.items()})
    if isinstance(value, (list, tuple)):
        return [_redact_value(key, item) for item in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return f"<{type(value).__name__}>"
