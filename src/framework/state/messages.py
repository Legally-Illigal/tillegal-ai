"""Message values and message-state schema."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Annotated, TypedDict
from uuid import uuid4

from src.framework.state.reducers import merge_messages


@dataclass(frozen=True)
class WorkflowMessage:
    """A serializable message exchanged by a workflow participant."""

    role: str
    content: str
    message_id: str = field(default_factory=lambda: str(uuid4()))
    name: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.role.strip():
            raise ValueError("message role must not be blank")
        if not self.message_id.strip():
            raise ValueError("message_id must not be blank")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        if any(not isinstance(key, str) or not key for key in self.metadata):
            raise ValueError("message metadata keys must be non-empty strings")
        if any(not isinstance(value, str) for value in self.metadata.values()):
            raise ValueError("message metadata values must be strings")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


class MessageState(TypedDict, total=False):
    """LangGraph-compatible state portion containing workflow messages."""

    messages: Annotated[list[WorkflowMessage | Mapping[str, object]], merge_messages]
