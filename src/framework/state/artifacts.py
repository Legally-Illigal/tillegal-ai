"""Typed, immutable workflow artifact values."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from uuid import uuid4


@dataclass(frozen=True)
class Artifact:
    """A named result or evidence item produced during a workflow."""

    name: str
    content: object
    content_type: str = "application/json"
    artifact_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("artifact name must not be blank")
        if not self.artifact_id.strip():
            raise ValueError("artifact_id must not be blank")
        if not self.content_type.strip():
            raise ValueError("content_type must not be blank")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        if any(not isinstance(key, str) or not key for key in self.metadata):
            raise ValueError("artifact metadata keys must be non-empty strings")
        if any(not isinstance(value, str) for value in self.metadata.values()):
            raise ValueError("artifact metadata values must be strings")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
