"""Run a paired offline experiment. Keep raw case-level traces and label provenance."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from statistics import median
from time import perf_counter

from ai_core.basic_rag import BasicRAG
from ai_core.bm25_retrieval import load_index
from ai_core.rag_generation import GenerationError
from ai_core.retrieval_runtime import ROOT
from src.applications.tillegal.graphs.legal_qa import LegalQA
from src.framework.llm.gateway import answer_provider

CASES = {
    "X01": "Người lao động được nghỉ hằng năm như thế nào?",
    "X02": "Thế nào là làm thêm giờ?",
    "X03": "Trích dẫn: đối thoại định kỳ",
    "X04": "qzzzxxyy qzzzyyyy",
}
INDEX = ROOT / "data/indexes/labor-pilot-3-t4-bm25/manifest.json"


def summarize(rows):
    successes = [r for r in rows if r["status"] != "FAILED"]
    return {"attempts": len(rows), "failures": len(rows)-len(successes),
            "abstentions": sum(r["status"] in {"ABSTAINED", "ABSTAINED_UNVERIFIED", "NO_EVIDENCE"} for r in successes),
            "median_wall_ms": round(median(r["elapsed_ms"] for r in rows), 1),
            "reported_tokens": {k: sum(u[k] for r in rows for u in r["usage"] if k in u)
                                if any(k in u for r in rows for u in r["usage"]) else None
                                for k in ("prompt_tokens", "completion_tokens")},
            "human_groundedness": None, "human_relevance": None, "human_citation_correctness": None,
            "human_unsupported_rate": None}


async def compare(args):
    config = {"TILLEGAL_ANSWER_PROVIDER": args.provider, "TILLEGAL_ANSWER_MODEL": args.model,
              "TILLEGAL_LOCAL_PORT": str(args.port), "TILLEGAL_RETRIEVAL_MODE": "bm25"}
    index = load_index(INDEX)
    basic = BasicRAG(index, answer_provider(config))
    graph = LegalQA(config)
    rows = []
    for qid, question in CASES.items():
        for mode in ("basic", "draft", "semantic"):
            started = perf_counter()
            rid = qid + "-" + mode
            try:
                if mode == "basic":
                    result = basic.answer(question, request_id=rid, top_k=1)
                    bundles = [result["evidence_bundle"]] if result["evidence_bundle"] else []
                    usage = [result["trace"].get("provider_response", {})]
                else:
                    result = await graph.answer(question, rid, 1, mode)
                    bundles = result["evidence_bundles"]
                    usage = [result["usage"], *(c["trace"]["usage"] for c in result["citation_checks"])]
            except (GenerationError, TimeoutError) as exc:
                result = {"status": "FAILED", "error": getattr(exc, "code", "TIMEOUT")}
                bundles, usage = [], []
            elapsed = (perf_counter()-started)*1000
            refs = {r["evidence_id"]: r for b in bundles for r in b["evidence"]}
            checks = result.get("citation_checks", [])
            citations = [r["evidence_id"] for r in result.get("candidate_citations", [])]
            ids = set(citations) | {c["evidence_id"] for c in checks}
            row = {"case": qid, "question": question, "mode": mode, "status": result["status"],
                   "error": result.get("error"), "elapsed_ms": round(elapsed, 1), "usage": usage,
                   "answer": result.get("answer"), "claims": result.get("claims"), "checks": checks,
                   "citations": citations, "sources": {k: {field: refs[k][field] for field in
                   ("quote", "quote_sha256", "chunk_id", "document_version_id","normalized_locator")} for k in ids if k in refs},
                   "retrieval": [{"status": b["status"], "query": b["query"], "seeds":
                   [g["retrieved_chunk_id"] for g in b["groups"]], "omitted": sum(len(g["omitted_chunk_ids"])
                   for g in b["groups"])} for b in bundles], "judge": result.get("judgments", [])}
            rows.append(row)
            print(qid, mode, row["status"], row["elapsed_ms"], flush=True)
    report = {"dataset": "exploratory-v1-no-human-labels", "provider": args.provider, "model": graph.provider.model,
              "index_id": index.index_id, "retrieval_mode":"bm25","top_k":1,
              "questions_sha256": hashlib.sha256(json.dumps(CASES, ensure_ascii=False).encode()).hexdigest(),
              "rows": rows, "summary": {mode: summarize([r for r in rows if r["mode"] == mode])
                                         for mode in ("basic", "draft", "semantic")}}
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["mock","local"], default="mock")
    parser.add_argument("--model", default="")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be a new file")
    asyncio.run(compare(args))
