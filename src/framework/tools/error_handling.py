"""Errors raised while validating and executing workflow tools."""

from pydantic import ValidationError


class ToolExecutionError(RuntimeError):
    """Raised when a tool handler fails."""


class ToolInputValidationError(ValueError):
    """Raised when tool arguments fail their declared schema."""


class ToolTimeoutError(TimeoutError):
    """Raised when a tool exceeds its configured execution timeout."""


def input_validation_error(error: ValidationError) -> ToolInputValidationError:
    """Build a concise validation error without echoing potentially sensitive inputs."""
    issues = error.errors(include_input=False, include_context=False, include_url=False)
    summary = "; ".join(f"{'.'.join(str(part) for part in issue['loc'])}: {issue['msg']}" for issue in issues)
    return ToolInputValidationError(f"Tool arguments are invalid: {summary}")
