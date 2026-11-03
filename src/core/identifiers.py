"""Utilities for creating and validating UUID identifiers."""

from uuid import UUID, uuid4


def new_id() -> UUID:
    """Create a new UUID4 identifier."""
    return uuid4()


def parse_id(value: str | UUID) -> UUID:
    """Parse a UUID identifier, preserving UUID instances as-is."""
    if isinstance(value, UUID):
        return value
    return UUID(value)
