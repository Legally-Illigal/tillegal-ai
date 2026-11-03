"""Shared state schema for LangGraph workflows."""

from typing import Annotated, TypedDict

from src.framework.state.artifacts import Artifact
from src.framework.state.messages import WorkflowMessage
from src.framework.state.reducers import append_unique, merge_artifacts, merge_messages, merge_metadata


class WorkflowState(TypedDict, total=False):
    """Common optional fields available to application workflow states."""

    run_id: str
    status: str
    messages: Annotated[list[WorkflowMessage | dict[str, object]], merge_messages]
    artifacts: Annotated[list[Artifact], merge_artifacts]
    metadata: Annotated[dict[str, object], merge_metadata]
    errors: Annotated[list[str], append_unique]


class ArtifactState(TypedDict, total=False):
    """LangGraph-compatible state portion containing workflow artifacts."""

    artifacts: Annotated[list[Artifact], merge_artifacts]
