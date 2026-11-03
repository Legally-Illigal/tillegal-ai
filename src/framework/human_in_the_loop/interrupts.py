"""LangGraph interrupts used by human review workflows."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langgraph.types import interrupt

if TYPE_CHECKING:
    from src.framework.human_in_the_loop.approvals import ApprovalDecision, ApprovalRequest


def interrupt_for_approval(request: ApprovalRequest) -> ApprovalDecision:
    """Suspend the current graph until a matching approval decision is resumed."""
    from src.framework.human_in_the_loop.approvals import ApprovalDecision

    response: Any = interrupt(request.model_dump(mode="json"))
    decision = ApprovalDecision.model_validate(response)
    if decision.approval_id != request.approval_id:
        raise ValueError("Approval decision does not match the pending request")
    return decision
