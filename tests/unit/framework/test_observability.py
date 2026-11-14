"""Tests for structured observability helpers."""

import json
import logging

from src.framework.observability.correlation import (
    bind_request_context,
    bind_workflow_run,
    current_correlation_context,
)
from src.framework.observability.events import log_event
from src.framework.observability.logging import JsonLogFormatter


def test_log_event_includes_context_and_redacts_sensitive_fields(caplog) -> None:
    with caplog.at_level(logging.INFO, logger="tillegal.observability"):
        with bind_request_context("request-123"):
            with bind_workflow_run("workflow-456"):
                log_event(
                    "model_call_completed",
                    component="llm.gateway",
                    provider="openai",
                    input_tokens=120,
                    prompt="sensitive user question",
                    api_key="do-not-log",
                    raw_content="sensitive legal text",
                )

    record = next(record for record in caplog.records if record.name == "tillegal.observability")
    event_data = record.event_data
    assert event_data["request_id"] == "request-123"
    assert event_data["workflow_run_id"] == "workflow-456"
    assert event_data["provider"] == "openai"
    assert event_data["input_tokens"] == 120
    assert event_data["prompt"] == "[REDACTED]"
    assert event_data["api_key"] == "[REDACTED]"
    assert event_data["raw_content"] == "[REDACTED]"
    assert current_correlation_context() == {}


def test_json_formatter_emits_valid_json() -> None:
    record = logging.LogRecord("test", logging.INFO, "", 0, "test event", (), None)
    record.event_data = {"event": "request_completed", "status_code": 200}

    formatted = JsonLogFormatter().format(record)

    assert json.loads(formatted) == {"event": "request_completed", "status_code": 200}


def test_json_formatter_includes_crawl_failure_diagnostics() -> None:
    record = logging.LogRecord("test", logging.ERROR, "", 0, "crawl failed", (), None)
    record.crawl_job_id = "job-123"
    record.crawl_date = "2026-11-09"
    record.error_category = "DatabaseRepositoryError"
    record.error_message = "PostgreSQL JSON serialization failed"

    payload = json.loads(JsonLogFormatter().format(record))

    assert payload["level"] == "ERROR"
    assert payload["message"] == "crawl failed"
    assert payload["crawl_job_id"] == "job-123"
    assert payload["crawl_date"] == "2026-11-09"
    assert payload["error_category"] == "DatabaseRepositoryError"
    assert payload["error_message"] == "PostgreSQL JSON serialization failed"
