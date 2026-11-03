"""Pure reducers for merging workflow state updates."""

from collections.abc import Mapping, Sequence
from typing import TypeVar

from src.framework.state.artifacts import Artifact

T = TypeVar("T")


def append_unique[T](current: Sequence[T] | None, updates: Sequence[T] | None) -> list[T]:
    """Append values not already present while preserving input order."""
    merged = list(current or ())
    for update in updates or ():
        if update not in merged:
            merged.append(update)
    return merged


def merge_messages[T](current: Sequence[T] | None, updates: Sequence[T] | None) -> list[T]:
    """Append messages, replacing existing entries that share a message ID."""
    merged = list(current or ())
    positions = {
        message_id: index for index, message in enumerate(merged) if (message_id := _message_id(message)) is not None
    }
    for message in updates or ():
        message_id = _message_id(message)
        if message_id is not None and message_id in positions:
            merged[positions[message_id]] = message
        else:
            if message_id is not None:
                positions[message_id] = len(merged)
            merged.append(message)
    return merged


def merge_artifacts(
    current: Sequence[Artifact] | None,
    updates: Sequence[Artifact] | None,
) -> list[Artifact]:
    """Append artifacts, replacing prior versions with the same artifact ID."""
    merged = list(current or ())
    positions = {artifact.artifact_id: index for index, artifact in enumerate(merged)}
    for artifact in updates or ():
        position = positions.get(artifact.artifact_id)
        if position is None:
            positions[artifact.artifact_id] = len(merged)
            merged.append(artifact)
        else:
            merged[position] = artifact
    return merged


def merge_metadata(
    current: Mapping[str, object] | None,
    updates: Mapping[str, object] | None,
) -> dict[str, object]:
    """Merge metadata maps, with the most recent update winning per key."""
    return {**(current or {}), **(updates or {})}


def _message_id(message: object) -> str | None:
    if isinstance(message, Mapping):
        value = message.get("id", message.get("message_id"))
    else:
        value = getattr(message, "id", getattr(message, "message_id", None))
    return value if isinstance(value, str) and value else None
