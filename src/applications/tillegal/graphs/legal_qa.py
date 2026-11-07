"""Stateless LangGraph workflow for the experimental pilot corpus."""
import asyncio
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from langsmith import tracing_context

from ai_core import retrieval_runtime
from ai_core.rag_generation import generation_messages, validate_draft
from src.applications.tillegal.graphs.citation_verification import check_candidates
from src.applications.tillegal.graphs.multi_agent import compile_multi
from src.applications.tillegal.tools.legal_retrieval import LegalRetrieval
from src.framework.llm.gateway import answer_provider
from src.framework.observability.correlation import bind_workflow_run
from src.framework.observability.events import log_event
from src.framework.tools.execution import ToolExecutor
from src.framework.tools.permissions import ToolPrincipal
from src.framework.tools.registry import ToolRegistry


class QAState(TypedDict, total=False):
    question: str
    request_id: str
    run_id: str
    top_k: int
    evidence_bundle: dict
    output: dict


class LegalQA:
    def __init__(self, config):
        self.provider = answer_provider(config)
        mode = config.get("TILLEGAL_RETRIEVAL_MODE", "bm25")
        rerank = config.get("TILLEGAL_RERANK", "false")
        if rerank not in ("true", "false"):
            raise ValueError("TILLEGAL_RERANK must be true or false")
        default = retrieval_runtime.ROOT / "data/indexes/labor-pilot-3-t4-bm25/manifest.json"
        retrieval = LegalRetrieval(Path(config.get("TILLEGAL_INDEX", default)), mode, rerank == "true")
        registry = ToolRegistry()
        registry.register(retrieval.tool())
        self.tools = ToolExecutor(registry)
        self.mode = mode
        self.active = asyncio.Semaphore(1)
        self.generation_lock = Lock()
        graph = StateGraph(QAState)
        graph.add_node("retrieve", self.retrieve)
        graph.add_node("draft", self.draft)
        graph.add_edge(START, "retrieve")
        graph.add_edge("retrieve", "draft")
        graph.add_edge("draft", END)
        self.graph = graph.compile()
        self.multi_graph = compile_multi(self.tools, answer_provider(config, profile="RESPONSE"), self.generation_lock,
                                        int(config.get("TILLEGAL_SEARCH_BUDGET", 4)),
                                        int(config.get("TILLEGAL_SEARCH_ROUNDS", 2)),
                                        verifier=answer_provider(config, profile="VERIFIER"),
                                        context_policy=config.get("TILLEGAL_CONTEXT_POLICY", "legacy"))

    async def retrieve(self, state):
        started = perf_counter()
        bundle = await self.tools.execute("legal_retrieval", {k: state[k] for k in
            ("question", "request_id", "top_k")}, principal=ToolPrincipal("pilot", frozenset({"pilot.read"})))
        log_event("retrieval_completed", component="legal_qa", run_id=state["run_id"],
                  duration_ms=(perf_counter()-started)*1000, backend=self.mode,
                  index_id=bundle["index_id"], evidence_status=bundle["status"])
        return {"evidence_bundle": bundle}

    def draft(self, state):
        started = perf_counter()
        bundle = state["evidence_bundle"]
        by_id = {item["evidence_id"]: item for item in bundle["evidence"]}
        output = {"status": "NO_EVIDENCE", "answer": None, "candidate_citations": [],
                  "usage_policy": "EXPERIMENTAL_ONLY", "verification_status": "NOT_PERFORMED",
                  "provider": self.provider.mode, "model": self.provider.model, "usage": {}}
        if by_id:
            if not self.generation_lock.acquire(blocking=False):
                raise BlockingIOError("provider busy")
            try:
                raw = self.provider.generate(generation_messages(state["question"], bundle))
            finally:
                self.generation_lock.release()
            draft = validate_draft(raw, set(by_id))
            output.update(status="ABSTAINED_UNVERIFIED" if draft["abstain"] else "DRAFT_UNVERIFIED",
                          answer=draft["draft_answer"], usage=getattr(raw, "metadata", {}),
                          candidate_citations=[dict(by_id[i], citation_status="CANDIDATE_UNVERIFIED")
                                               for i in draft["candidate_evidence_ids"]])
        output["citation_checks"] = check_candidates(bundle, output["candidate_citations"])
        log_event("draft_completed", component="legal_qa", run_id=state["run_id"],
                  duration_ms=(perf_counter()-started)*1000, status=output["status"],
                  model=self.provider.model, provider=self.provider.mode, usage=output["usage"],
                  verification_status=output["verification_status"])
        return {"output": output}

    async def answer(self, question, request_id, top_k, workflow="basic"):
        if self.active.locked():
            raise BlockingIOError("worker busy")
        async with self.active, asyncio.timeout(60):
            run_id = str(uuid4())
            with bind_workflow_run(run_id), tracing_context(enabled=False):
                if workflow in {"multi_agent", "draft", "semantic"}:
                    result = await self.multi_graph.ainvoke({"question": question, "request_id": request_id,
                        "run_id": run_id, "top_k": top_k, "workflow": workflow}, config={"recursion_limit": 12})
                    return {**result["output"], "request_id": request_id, "run_id": run_id}
                result = await self.graph.ainvoke({"question": question, "request_id": request_id,
                    "run_id": run_id, "top_k": top_k}, config={"recursion_limit": 4})
            return {**result["output"], "evidence_bundle": result["evidence_bundle"],
                    "request_id": request_id, "run_id": run_id}
