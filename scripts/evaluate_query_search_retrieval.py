"""Read-only Query-plan replay against the real Supabase corpus; no model downloads."""

import argparse
import asyncio
import hashlib
import json
import os
import time
from functools import wraps
from pathlib import Path
from unittest.mock import patch

from dotenv import dotenv_values

from scripts.evaluate_query_search import matches
from src.applications.tillegal.agents.query.agent import QueryPlan
from src.applications.tillegal.agents.search.agent import SearchOptions, search
from src.applications.tillegal.retrieval.hybrid_models import HybridConfig
from src.applications.tillegal.retrieval.reranking_models import RerankConfig
from src.core.config import load_settings
from src.integrations.embeddings.cross_encoder_reranker import LocalCrossEncoder
from src.integrations.embeddings.e5_query_encoder import E5QueryEncoder
from src.retrieval_bootstrap import create_retrieval_service

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path.home() / ".cache/huggingface/hub"
DENSE = CACHE / "models--intfloat--multilingual-e5-small/snapshots/614241f622f53c4eeff9890bdc4f31cfecc418b3"
CE = CACHE / "models--cross-encoder--mmarco-mMiniLMv2-L12-H384-v1/snapshots/1427fd652930e4ba29e8149678df786c240d8825"


def sanitize(value):
    if isinstance(value, dict):
        return {
            key: (
                "[REDACTED]"
                if any(word in key.lower() for word in ("authorization", "api_key", "password", "secret"))
                else sanitize(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, (tuple, list)):
        return [sanitize(item) for item in value]
    return value


def checks(result: dict, expected: dict) -> dict:
    groups = result["evidence"]
    occurrences = [occurrence for group in groups for occurrence in group.occurrences]
    valid = all(
        result["requests"][o.subquery_index].query == o.query
        and str(result["responses"][o.response_index].request_id) == o.request_id
        and any(
            item.retrieval_chunk_id == group.evidence.retrieval_chunk_id
            and item.content_sha256 == group.evidence.content_sha256
            for item in result["responses"][o.response_index].evidence
        )
        for group in groups
        for o in group.occurrences
    )
    content = " ".join(group.evidence.title + " " + group.evidence.content for group in groups)
    keys = [
        group.evidence.model_dump_json(exclude={"rank", "raw_score", "score_kind", "retrieval_method"})
        for group in groups
    ]
    return {
        "evidence_groups": len(groups),
        "occurrences": len(occurrences),
        "duplicates_collapsed": len(occurrences) - len(groups),
        "provenance_links_valid": valid if occurrences else None,
        "content_hashes_match": all(
            hashlib.sha256(group.evidence.content.encode()).hexdigest() == group.evidence.content_sha256
            for group in groups
        )
        if groups
        else None,
        "unique_source_payloads": len(keys) == len(set(keys)) if keys else None,
        "source_ids_present": all(
            group.evidence.source_document_id and group.evidence.document_structure_id for group in groups
        )
        if groups
        else None,
        "objective_topic_matches_proxy": sum(matches(pattern, content) for pattern in expected["expected_issues"]),
        "objective_topic_total": len(expected["expected_issues"]),
        "relevance_assessment": "LEXICAL_PROXY_ONLY_NO_RELEVANCE_JUDGMENTS",
    }


async def run(args):
    if args.output.exists():
        raise ValueError("Preserve previous output; choose a new result path")
    data = json.loads(args.plans.read_text(encoding="utf-8"))
    plans = {row["id"]: row for row in data["rows"] if row["status"] == "OK"}
    cases = {
        case["id"]: case
        for case in json.loads((ROOT / "evaluation/query_search/cases.json").read_text(encoding="utf-8"))["cases"]
    }
    env = {**{key: value for key, value in dotenv_values(ROOT / ".env").items() if value is not None}, **os.environ}
    settings = load_settings(environ=env).supabase
    report = {
        "plans_artifact": str(args.plans),
        "prompt_sha256": data["prompt_sha256"],
        "model": data.get("model"),
        "live_gemini_replayed_not_recalled": data["mode"] == "gemini",
        "database": "REAL_SUPABASE_READ_ONLY",
        "as_of_date": args.as_of_date,
        "dense_path_exists": DENSE.is_dir(),
        "reranker_path_exists": CE.is_dir(),
        "rows": [],
    }
    hybrid = HybridConfig(bm25_candidates=10, dense_candidates=10)
    started = time.perf_counter()
    service = create_retrieval_service(
        settings, dense_model_path=DENSE if DENSE.is_dir() else None, hybrid_config=hybrid, timeout_seconds=30
    )
    reranked = create_retrieval_service(
        settings,
        dense_model_path=DENSE if DENSE.is_dir() else None,
        hybrid_config=hybrid,
        timeout_seconds=30,
        rerank_config=RerankConfig(
            enabled=True, model_path=CE, candidate_pool=8, inference_timeout_seconds=25, total_timeout_seconds=40
        ),
    )
    report["bootstrap_ms"] = round((time.perf_counter() - started) * 1000, 2)
    report["model_initialization"] = []
    if args.warm_models and not args.bm25_only:
        for name, loader in [
            ("e5_base", service._query_embedder._get_model),
            ("e5_rerank", reranked._query_embedder._get_model),
            ("cross_encoder", reranked._pair_scorer._load),
        ]:
            started = time.perf_counter()
            try:
                async with asyncio.timeout(90):
                    await asyncio.to_thread(loader)
                initialization = {"model": name, "status": "INITIALIZED"}
            except Exception as error:
                initialization = {"model": name, "status": "BLOCKED", "error_type": type(error).__name__}
            initialization["ms"] = round((time.perf_counter() - started) * 1000, 2)
            report["model_initialization"].append(initialization)
            print(json.dumps(initialization), flush=True)
    timings = []

    def timed(original, name):
        @wraps(original)
        def wrapper(*a, **kw):
            started = time.perf_counter()
            try:
                return original(*a, **kw)
            finally:
                timings.append({"stage": name, "ms": round((time.perf_counter() - started) * 1000, 2)})

        return wrapper

    schedule = [("Q001", mode) for mode in ("bm25", "dense", "hybrid", "rerank")]
    schedule += [(case_id, "bm25") for case_id in ("Q004", "Q010")]
    if args.bm25_only:
        schedule = [(case_id, "bm25") for case_id in args.case_ids.split(",")]
    with (
        patch.object(E5QueryEncoder, "_get_model", timed(E5QueryEncoder._get_model, "e5_load_or_cached")),
        patch.object(LocalCrossEncoder, "_load", timed(LocalCrossEncoder._load, "reranker_cold_load")),
    ):
        for case_id, mode in schedule:
            if case_id not in plans:
                report["rows"].append({"id": case_id, "mode": mode, "status": "BLOCKED_QUERY_PLAN_UNAVAILABLE"})
                continue
            plan = QueryPlan.model_validate(plans[case_id]["plan"]).model_dump()
            row = {
                "id": case_id,
                "mode": mode,
                "configured": True,
                "local_dense_available": DENSE.is_dir(),
                "local_reranker_available": CE.is_dir(),
            }
            timings.clear()
            started = time.perf_counter()
            try:
                result = await search(
                    plan,
                    reranked if mode == "rerank" else service,
                    SearchOptions(
                        mode="hybrid" if mode == "rerank" else mode,
                        top_k=3,
                        as_of_date=args.as_of_date,
                        allowed_usage_policies=("EXPERIMENTAL_ONLY",),
                    ),
                )
                row.update(
                    status=result["status"], completeness=result["completeness"], checks=checks(result, cases[case_id])
                )
                row["requests"] = [request.model_dump(mode="json") for request in result["requests"]]
                row["responses"] = [response.model_dump(mode="json") for response in result["responses"]]
                row["aggregated_evidence"] = [group.model_dump(mode="json") for group in result["evidence"]]
                row["warnings"] = list(result["warnings"])
                row["errors"] = [error.model_dump(mode="json") for error in result["errors"]]
                row["reranking_statuses"] = [
                    response.reranking.status for response in result["responses"] if hasattr(response, "reranking")
                ]
                row["reranking_diagnostics"] = [
                    response.reranking.diagnostics.model_dump(mode="json")
                    for response in result["responses"]
                    if hasattr(response, "reranking") and response.reranking.diagnostics
                ]
            except Exception as error:
                row.update(status="BLOCKED", error_type=type(error).__name__)
            row["timings"] = list(timings)
            row["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
            report["rows"].append(row)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(sanitize(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(
                json.dumps(
                    {
                        key: row.get(key)
                        for key in (
                            "id",
                            "mode",
                            "status",
                            "completeness",
                            "checks",
                            "latency_ms",
                            "errors",
                            "reranking_statuses",
                        )
                    }
                ),
                flush=True,
            )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plans", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--bm25-only", action="store_true")
    parser.add_argument("--case-ids", default="Q001,Q004,Q010", help="Case IDs for BM25-only replay")
    parser.add_argument(
        "--warm-models", action="store_true", help="Measure local initialization separately from retrieval"
    )
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
