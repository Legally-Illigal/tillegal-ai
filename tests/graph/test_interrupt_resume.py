"""Tests for pausing and resuming a graph for human approval."""

from typing import Any, Literal

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START

from src.framework.graphs.compiler import compile_graph
from src.framework.graphs.factory import create_state_graph
from src.framework.human_in_the_loop import (
    ApprovalDecision,
    ApprovalRequest,
    ApprovalState,
    approval_gate,
    approval_resume_command,
    approval_route,
)


@pytest.mark.parametrize("decision_value", ["approve", "reject"])
def test_approval_graph_pauses_and_resumes(decision_value: Literal["approve", "reject"]) -> None:
    request = ApprovalRequest(
        approval_id="review-123",
        title="Review legal answer",
        description="Check the draft before it is returned to the user.",
        details={"draft": "Draft response"},
    )
    builder = create_state_graph(ApprovalState)
    builder.add_node("human_review", approval_gate)
    builder.add_node("approved", lambda _: {"outcome": "approved"})
    builder.add_node("rejected", lambda _: {"outcome": "rejected"})
    builder.add_edge(START, "human_review")
    builder.add_conditional_edges(
        "human_review",
        approval_route,
        {"approve": "approved", "reject": "rejected"},
    )
    builder.add_edge("approved", END)
    builder.add_edge("rejected", END)
    graph = compile_graph(builder, checkpointer=InMemorySaver(), name="approval-test")
    config: dict[str, Any] = {"configurable": {"thread_id": f"approval-{decision_value}"}}

    pending = graph.invoke({"approval_request": request}, config)

    assert pending["__interrupt__"][0].value == request.model_dump(mode="json")

    decision = ApprovalDecision(
        approval_id=request.approval_id,
        decision=decision_value,
        comment="Reviewed by a human.",
    )
    resumed = graph.invoke(approval_resume_command(decision), config)

    assert resumed["approval_decision"] == decision.model_dump(mode="json")
    expected_outcome = {"approve": "approved", "reject": "rejected"}[decision_value]
    assert resumed["outcome"] == expected_outcome
