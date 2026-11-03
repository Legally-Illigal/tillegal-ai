"""Compile LangGraph builders into executable workflows."""

from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph


def compile_graph[StateT](
    builder: StateGraph[StateT, Any, Any, Any],
    *,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
    name: str | None = None,
) -> CompiledStateGraph[StateT, Any, Any, Any]:
    """Compile a graph, optionally enabling persistence through a checkpointer."""
    return builder.compile(checkpointer=checkpointer, name=name)
