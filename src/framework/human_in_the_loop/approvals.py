"""Approval contracts and a reusable LangGraph approval node."""

from collections.abc import Mapping
from typing import Any, Literal, NotRequired, TypedDict

from pydantic import BaseModel, ConfigDict, Field

from src.core.identifiers import new_id


class ApprovalRequest(BaseModel):
    """Information presented to a human reviewer."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    approval_id: str = Field(default_factory=lambda: str(new_id()), min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=4000)
    details: dict[str, Any] = Field(default_factory=dict)


class ApprovalDecision(BaseModel):
    """A reviewer's decision for one approval request."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    approval_id: str = Field(min_length=1, max_length=128)
    decision: Literal["approve", "reject"]
    comment: str | None = Field(default=None, max_length=4000)


class ApprovalState(TypedDict):
    """State fields consumed and produced by :func:`approval_gate`."""

    approval_request: ApprovalRequest | Mapping[str, Any]
    approval_decision: NotRequired[dict[str, Any]]
    outcome: NotRequired[str]


def approval_gate(state: ApprovalState) -> dict[str, Any]:
    """Pause the graph for a human decision and store the validated result."""
    from src.framework.human_in_the_loop.interrupts import interrupt_for_approval

    request = ApprovalRequest.model_validate(state["approval_request"])
    decision = interrupt_for_approval(request)
    return {"approval_decision": decision.model_dump(mode="json")}


def approval_route(state: Mapping[str, Any]) -> Literal["approve", "reject"]:
    """Return the route selected by the completed approval gate."""
    decision = ApprovalDecision.model_validate(state["approval_decision"])
    return decision.decision
