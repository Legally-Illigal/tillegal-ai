"""Reusable workflow state schemas, artifacts, and merge reducers."""

from src.framework.state.artifacts import Artifact
from src.framework.state.base import ArtifactState, WorkflowState
from src.framework.state.messages import MessageState, WorkflowMessage
from src.framework.state.reducers import append_unique, merge_artifacts, merge_messages, merge_metadata

__all__ = [
    "Artifact",
    "ArtifactState",
    "MessageState",
    "WorkflowMessage",
    "WorkflowState",
    "append_unique",
    "merge_artifacts",
    "merge_messages",
    "merge_metadata",
]
