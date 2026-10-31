"""Execution and outbox data transfer objects."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OutboxEvent(BaseModel):
    """A claimed event ready to publish to the execution queue."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    event_type: str
    payload: dict[str, Any]
    attempts: int
