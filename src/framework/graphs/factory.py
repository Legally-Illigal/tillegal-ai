"""Factories for LangGraph state graph builders."""

from typing import Any

from langgraph.graph import StateGraph


def create_state_graph[StateT](
    state_schema: type[StateT],
) -> StateGraph[StateT, Any, Any, Any]:
    """Create a graph builder for the supplied workflow state schema."""
    return StateGraph(state_schema)
