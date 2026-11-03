"""Helpers for resuming a graph after human review."""

from langgraph.types import Command

from src.framework.human_in_the_loop.approvals import ApprovalDecision


def approval_resume_command(decision: ApprovalDecision) -> Command:
    """Create the LangGraph command that supplies a validated approval decision."""
    return Command(resume=decision.model_dump(mode="json"))
