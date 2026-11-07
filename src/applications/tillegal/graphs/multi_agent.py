"""Bounded query/search/judge/refine/response/verify graph for the pilot."""
from typing import TypedDict
from time import perf_counter

from langgraph.graph import END, START, StateGraph

from src.applications.tillegal.agents.judge.agent import judge
from src.applications.tillegal.agents.query.agent import understand
from src.applications.tillegal.agents.response.agent import respond
from src.applications.tillegal.agents.search.agent import search
from src.applications.tillegal.graphs.citation_verification import verify_claims
from src.applications.tillegal.graphs import semantic
from src.applications.tillegal.agents.judge.context_selection import select_context, context_judge


class MultiState(TypedDict, total=False):
    question: str
    request_id: str
    run_id: str
    top_k: int
    plan: dict
    pending: list[str]
    bundles: list[dict]
    search_trace: list[dict]
    evidence: dict
    new_count: int
    iteration: int
    judgments: list[dict]
    proposals: list[dict]
    usage: dict
    output: dict
    workflow: str
    context_selection: dict
    stage_timings: list[dict]


def compile_multi(tools, provider, lock, budget=4, iterations=2, verifier=None, context_policy="legacy"):
    if context_policy not in {"legacy", "context", "context_judge"}:
        raise ValueError("Invalid context policy")
    if not 1 <= budget <= 6 or not 1 <= iterations <= 3:
        raise ValueError("Pilot limits: 1–6 retrievals, 1–3 search rounds")

    def query_node(state):
        plan = understand(state["question"])
        return {"plan": plan, "pending": [] if plan["clarification"] else [q["text"] for q in plan["subqueries"]]}

    async def search_node(state):
        return await search(state, tools, budget)

    def judge_node(state):
        started = perf_counter()
        decision = judge(state, budget, iterations)
        update = {}
        if context_policy != "legacy":
            context = select_context(state)
            update["context_selection"] = context
            if context_policy == "context_judge":
                decision = context_judge(dict(state, context_selection=context), decision, budget, iterations)
            else:
                decision["selected"] = context["selected"]
                if (decision["jurisdiction"] == "OUTSIDE_VN_PILOT"
                        or "COMPETING_DOCUMENT_VERSIONS" in decision["gaps"]
                        or set(context["selected"]) & set(decision["outside_reported_period"])):
                    decision["selected"] = []
        update.update(judgments=[*state.get("judgments", []), decision], pending=decision["refinement"],
                      stage_timings=[*state.get("stage_timings", []),
                         {"stage":"judge_and_context", "elapsed_ms":(perf_counter()-started)*1000,
                          "context_ms":update.get("context_selection", {}).get("elapsed_ms", 0)}])
        return update

    def response_node(state):
        if state.get("workflow") in {"draft", "semantic"}:
            return semantic.generate_claims(state, provider, lock)
        return respond(state, provider, lock)

    def verify_node(state):
        if state.get("workflow") in {"draft", "semantic"}:
            result = semantic.finish(state, provider, verifier if state["workflow"] == "semantic" else None, lock)
            result["output"]["context_selection"] = state.get("context_selection", {})
            result["output"]["stage_timings"] = state["stage_timings"]
            return result
        decision = state["judgments"][-1]
        checks, claims, citations = verify_claims(state["evidence"], decision["selected"], state["proposals"])
        limitation = "Chưa xác minh hiệu lực, ngoại lệ và khả năng áp dụng cho tình huống cụ thể."
        status = "ABSTAINED"
        if claims:
            status = "EXTRACTIVE_DRAFT" if decision["decision"] == "SUFFICIENT" else "PARTIAL"
        facts = [c["text"] for c in claims]
        conclusion = state["plan"]["clarification"] or (
            "Đã tìm thấy đoạn văn bản phù hợp trong bộ dữ liệu thử nghiệm." if claims else
            "Chưa đủ căn cứ để trả lời câu hỏi."
        )
        return {"output": {"status": status, "answer": "\n\n".join([*facts, conclusion, limitation]),
                           "claims": claims, "candidate_citations": citations, "citation_checks": checks,
                           "interpretation": conclusion, "limitations": [limitation, *decision["gaps"]],
                           "query_plan": state["plan"], "judgments": state["judgments"],
                           "retrieval_trace": state["search_trace"], "evidence_bundles": state["bundles"],
                           "provider": provider.mode, "model": provider.model, "usage": state["usage"],
                           "context_selection":state.get("context_selection", {}),
                           "stage_timings":state["stage_timings"],
                           "usage_policy": "EXPERIMENTAL_ONLY", "verification_status": "LEGAL_SUPPORT_NOT_EVALUATED"}}

    graph = StateGraph(MultiState)
    for name, node in (("query", query_node), ("search", search_node), ("judge", judge_node),
                       ("response", response_node), ("verify", verify_node)):
        graph.add_node(name, node)
    graph.add_edge(START, "query")
    graph.add_edge("query", "search")
    graph.add_edge("search", "judge")
    graph.add_conditional_edges("judge", lambda s: "search" if s["judgments"][-1]["stop"] == "REFINE"
                                else "response", ["search", "response"])
    graph.add_edge("response", "verify")
    graph.add_edge("verify", END)
    return graph.compile()
