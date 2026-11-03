"""Tests for shared core utilities."""

from datetime import UTC
from uuid import UUID

import pytest

from src.core.clock import SystemClock, utc_now
from src.core.constants import DEFAULT_SERVICE_NAME, REDACTED_VALUE
from src.core.exceptions import ConfigurationError, CoreError, InvariantViolationError
from src.core.identifiers import new_id, parse_id
from src.core.result import Failure, Success
from src.core.security import redact_fields


def test_system_clock_returns_aware_utc_time() -> None:
    timestamp = SystemClock().now()

    assert timestamp.tzinfo is UTC
    assert utc_now().utcoffset() is not None


def test_core_constants_and_exception_hierarchy() -> None:
    assert DEFAULT_SERVICE_NAME == "tillegal-ai"
    assert issubclass(ConfigurationError, ValueError)
    assert issubclass(ConfigurationError, CoreError)
    assert issubclass(InvariantViolationError, CoreError)


def test_identifier_generation_and_parsing() -> None:
    identifier = new_id()

    assert isinstance(identifier, UUID)
    assert parse_id(str(identifier)) == identifier
    assert parse_id(identifier) is identifier

    with pytest.raises(ValueError):
        parse_id("not-a-uuid")


def test_success_result_transforms_and_unwraps_value() -> None:
    result = Success(2)

    assert result.is_success
    assert not result.is_failure
    assert result.map(lambda value: value * 3).unwrap() == 6
    assert result.unwrap() == 2
    with pytest.raises(ValueError, match="no error"):
        result.unwrap_error()


def test_failure_result_preserves_and_transforms_error() -> None:
    error = ValueError("invalid input")
    result = Failure(error)

    assert result.is_failure
    assert not result.is_success
    assert result.map(lambda value: value * 2) is result
    assert result.unwrap_error() is error
    transformed_error = result.map_error(lambda failure: RuntimeError(str(failure))).unwrap_error()
    assert isinstance(transformed_error, RuntimeError)
    assert str(transformed_error) == "invalid input"
    with pytest.raises(ValueError, match="invalid input"):
        result.unwrap()


def test_redaction_recurses_and_returns_json_safe_values() -> None:
    payload = {
        "api_key": "do-not-log",
        "metadata": {"database_url": "postgres://secret"},
        "items": [{"prompt": "private text"}, "visible"],
        "count": 2,
        "object": object(),
    }

    redacted = redact_fields(payload)

    assert redacted["api_key"] == REDACTED_VALUE
    assert redacted["metadata"] == {"database_url": REDACTED_VALUE}
    assert redacted["items"] == [{"prompt": REDACTED_VALUE}, "visible"]
    assert redacted["count"] == 2
    assert redacted["object"] == "<object>"
    assert payload["api_key"] == "do-not-log"
