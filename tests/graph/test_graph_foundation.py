"""Tests for the reusable LangGraph foundation."""

from typing import TypedDict

from langgraph.graph import END, START

from src.framework.graphs.compiler import compile_graph
from src.framework.graphs.factory import create_state_graph


class CounterState(TypedDict):
    value: int


def test_compiled_graph_runs_from_start_to_end() -> None:
    builder = create_state_graph(CounterState)
    builder.add_node("increment", lambda state: {"value": state["value"] + 1})
    builder.add_edge(START, "increment")
    builder.add_edge("increment", END)

    graph = compile_graph(builder, name="counter")

    assert graph.invoke({"value": 1}) == {"value": 2}
