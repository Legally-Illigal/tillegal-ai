"""Shared exceptions for cross-layer failures."""


class CoreError(Exception):
    """Base class for errors raised by shared core utilities."""


class ConfigurationError(CoreError, ValueError):
    """Raised when application configuration is invalid."""


class InvariantViolationError(CoreError, RuntimeError):
    """Raised when an internal system invariant is violated."""
