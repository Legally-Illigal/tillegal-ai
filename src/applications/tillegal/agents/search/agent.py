"""Budgeted search. Canonical bundles remain intact per tool invocation."""
from time import perf_counter

from src.framework.tools.error_handling import ToolExecutionError
from src.framework.tools.permissions import ToolPrincipal


async def search(state, tools, limit):
    bundles = list(state.get("bundles", []))
    trace = list(state.get("search_trace", []))
    evidence = dict(state.get("evidence", {}))
    previous = len(evidence)
    for query in state["pending"][:limit - len(trace)]:
        started = perf_counter()
        bundle = await tools.execute("legal_retrieval", {
            "question": query, "request_id": state["request_id"], "top_k": state["top_k"]
        }, principal=ToolPrincipal("pilot", frozenset({"pilot.read"})))
        if bundle["request_id"] != state["request_id"] or (bundles and bundle["index_id"] != bundles[0]["index_id"]):
            raise ToolExecutionError("Incompatible evidence bundle")
        bundles.append(bundle)
        for row in bundle["evidence"]:
            existing = evidence.setdefault(row["evidence_id"], row)
            if existing != row:
                raise ToolExecutionError("Inconsistent evidence identity")
        trace.append({"query": query, "bundle_id": bundle["bundle_id"], "status": bundle["status"],
                      "index_id": bundle["index_id"], "elapsed_ms": (perf_counter()-started)*1000})
    return {"bundles": bundles, "evidence": evidence, "search_trace": trace,
            "new_count": len(evidence)-previous, "iteration": state.get("iteration", 0)+1}
