"""Bounded read-only relevance investigation; never calls an LLM or downloads models."""

import argparse
import asyncio
import hashlib
import json
import os
import time
from pathlib import Path
from statistics import median

from dotenv import dotenv_values

from scripts.evaluate_query_relevance import RUBRIC
from scripts.evaluate_query_search_retrieval import CE, DENSE, checks, sanitize
from src.applications.tillegal.agents.query.agent import QueryPlan
from src.applications.tillegal.agents.search.agent import SearchOptions, _finish, search
from src.applications.tillegal.retrieval.contracts import RetrievalRequest, RetrievalResponse
from src.applications.tillegal.retrieval.hybrid_models import HybridConfig
from src.applications.tillegal.retrieval.reranking_models import RerankConfig
from src.core.config import load_settings
from src.retrieval_bootstrap import create_retrieval_service

ROOT = Path(__file__).resolve().parents[1]
PRIOR = ROOT / "evaluation/query_search/semantic_v2"
CASES = ("Q001", "Q004", "Q005", "Q007", "Q019", "Q022", "Q025", "Q040")
# Fixed before experiments. Research variants only: not generated legal conclusions.
FOCUSED = {
    "Q001": ["điều kiện có hiệu lực của giao dịch dân sự hợp đồng"],
    "Q004": [
        "người lao động đơn phương chấm dứt hợp đồng lao động báo trước",
        "người lao động chấm dứt hợp đồng lao động bồi thường",
    ],
    "Q022": ["Điều 35 Bộ luật Lao động 45/2019/QH14"],
    "Q040": ["nghĩa vụ trả nợ của bên vay", "thực hiện nghĩa vụ bảo lãnh"],
}
SOURCE_FIELDS = (
    "id,title,document_number,source_id,source_record_id,source_snapshot_id,source_url,"
    "usage_policy,issued_on,effective_from,effective_to,updated_at"
)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    path.write_text(json.dumps(sanitize(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_review(pool, runs):
    """Join original rows with native query context; never import provisional labels."""
    variants = {}
    for run in runs:
        if "responses" not in run:
            continue
        for index, response in enumerate(run["responses"]):
            for item in response["evidence"]:
                variants.setdefault((run["id"], index, item["rank"], item["retrieval_chunk_id"]), []).append(run)
    rows = []
    for row in pool["rows"]:
        candidates = variants[(row["case_id"], row["query_index"], row["rank"], row["chunk_id"])]
        # Preserve variant identity even when both plans use identical query text.
        matches = [
            r
            for r in candidates
            if hashlib.sha256(r["variant"].encode()).hexdigest()[:8] == row["blind_variant_token"]
            and r["requests"][row["query_index"]]["query"] == row["search_objective"]
        ]
        if len(matches) != 1:
            raise ValueError("Review row must resolve to exactly one variant/query")
        run = matches[0]
        plan = run["plan"]
        links = next(
            (
                item["issue_indices"]
                for item in plan.get("search_objectives", [])
                if item["query_index"] == row["query_index"]
            ),
            [],
        )
        response = run["responses"][row["query_index"]]
        evidence = next(e for e in response["evidence"] if e["retrieval_chunk_id"] == row["chunk_id"])
        rows.append(
            {
                **row,
                "legal_issue": [plan["issues"][i] for i in links],
                "issue_association": "EXPLICIT_PLAN_LINK" if links else "UNMAPPED_LEGACY_OBJECTIVE",
                "search_objective": [plan["issues"][i] for i in links] or [row["search_objective"]],
                "query": response["query"],
                "query_source": run["variant"],
                "retrieval_mode": response["mode"],
                "native_rank": evidence["rank"],
                "raw_score": evidence["raw_score"],
                "score_kind": evidence["score_kind"],
                "index": response["index"],
                "as_of_date": response["as_of_date"],
                "source_metadata": evidence["source_metadata"],
                "temporal_metadata": {
                    k: evidence.get(k)
                    for k in ("issued_on", "effective_from", "effective_to", "effect_status_reported")
                },
                "label": None,
                "label_source": "unlabeled",
                "reviewer": None,
                "reason": None,
            }
        )
    return {
        "rubric": RUBRIC,
        "human_labels": 0,
        "provisional_labels_imported": False,
        "expert_metrics": None,
        "rows": rows,
    }


def inspect_native(run):
    """Check every native chunk survives aggregation, including rank, plus explicit issue links."""
    if "responses" not in run:
        return {"status": run["status"], "auditable": False}
    native = []
    for i, response in enumerate(run["responses"]):
        for e in response["evidence"]:
            native.append((i, e["retrieval_chunk_id"], e["content_sha256"], e["rank"], e["raw_score"]))
    observed = [
        (
            o["response_index"],
            group["evidence"]["retrieval_chunk_id"],
            group["evidence"]["content_sha256"],
            o["rank"],
            o["raw_score"],
        )
        for group in run["evidence"]
        for o in group["occurrences"]
    ]
    return {
        "auditable": True,
        "native_items": len(native),
        "aggregated_occurrences": len(observed),
        "all_native_occurrences_preserved": sorted(native) == sorted(observed),
        "explicit_issue_links_preserved": all(
            list(o.get("issue_indices", []))
            == next(
                (
                    link["issue_indices"]
                    for link in run["plan"].get("search_objectives", [])
                    if link["query_index"] == o["subquery_index"]
                ),
                [],
            )
            for group in run["evidence"]
            for o in group["occurrences"]
        ),
        "checks": run["checks"],
        "warnings": run["warnings"],
        "status": run["status"],
    }


def offline(output):
    pool = load(PRIOR / "relevance/pool.json")
    runs = load(PRIOR / "relevance/runs.json")
    save(output / "human_review.json", build_review(pool, runs))
    save(
        output / "saved_search_audit.json",
        [{"id": run["id"], "variant": run["variant"], **inspect_native(run)} for run in runs],
    )
    cases = {c["id"]: c for c in load(ROOT / "evaluation/query_search/cases.json")["cases"]}
    save(
        output / "case_audit.json",
        [
            {
                "id": case_id,
                "question": cases[case_id]["question"],
                "authored_expectations": cases[case_id],
                "runs": [run for run in runs if run["id"] == case_id],
            }
            for case_id in CASES
        ],
    )


async def metadata(client):
    """Paginate visible source identities with before/after counts; not global visibility."""
    fields = SOURCE_FIELDS
    before = await asyncio.to_thread(
        lambda: client.table("source_documents").select("id", count="exact").limit(0).execute()
    )
    rows, pages = [], []
    for start in range(0, min(before.count or 0, 1000), 100):
        response = await asyncio.to_thread(
            lambda start=start: (
                client.table("source_documents").select(fields).order("id").range(start, start + 99).execute()
            )
        )
        pages.append({"offset": start, "rows": len(response.data)})
        rows.extend(response.data)
    after = await asyncio.to_thread(
        lambda: client.table("source_documents").select("id", count="exact").limit(0).execute()
    )
    chunk_count = await asyncio.to_thread(
        lambda: client.table("retrieval_chunks").select("id", count="exact").limit(0).execute()
    )
    indexes = {}
    for table in ("sparse_indexes", "dense_indexes"):
        response = await asyncio.to_thread(lambda table=table: client.table(table).select("*").limit(10).execute())
        indexes[table] = response.data
    return {
        "visibility": "CURRENT_CREDENTIAL_VISIBLE_ROWS_ONLY",
        "snapshot": False,
        "count_before": before.count,
        "count_after": after.count,
        "unique_ids": len({r["id"] for r in rows}),
        "pages": pages,
        "enumeration_complete_observed": before.count == after.count == len(rows) == len({r["id"] for r in rows}),
        "visible_chunk_count": chunk_count.count,
        "sources": rows,
        "indexes": indexes,
    }


async def live(output):
    env = {**{k: v for k, v in dotenv_values(ROOT / ".env").items() if v is not None}, **os.environ}
    settings = load_settings(environ=env).supabase
    hybrid = HybridConfig(bm25_candidates=10, dense_candidates=10)
    base = create_retrieval_service(
        settings, dense_model_path=DENSE if DENSE.is_dir() else None, hybrid_config=hybrid, timeout_seconds=40
    )
    reranked = create_retrieval_service(
        settings,
        dense_model_path=DENSE if DENSE.is_dir() else None,
        hybrid_config=hybrid,
        timeout_seconds=40,
        rerank_config=RerankConfig(
            enabled=True, model_path=CE, candidate_pool=10, inference_timeout_seconds=35, total_timeout_seconds=75
        ),
    )
    # Share one local encoder, initialized before timed requests; sequential CPU inference.
    reranked._query_embedder = base._query_embedder
    save(output / "coverage.json", await metadata(base._sources._client))
    report = {
        "new_gemini_calls": 0,
        "read_only": True,
        "model_initialization": [],
        "candidate_depth": 10,
        "inspection_prefixes": [3, 5, 10],
        "prefix_note": "Single depth-10 request; prefixes are not independent top-k runs.",
        "consistency": "BEST_EFFORT_NO_TRANSACTION_SNAPSHOT",
        "rows": [],
    }
    for name, loader in [
        ("e5", base._query_embedder._get_model if base._query_embedder else None),
        ("cross_encoder", reranked._pair_scorer._load if CE.is_dir() else None),
    ]:
        started = time.perf_counter()
        try:
            if loader is None:
                raise FileNotFoundError("local checkpoint")
            await asyncio.to_thread(loader)
            item = {"name": name, "status": "INITIALIZED"}
        except Exception as error:
            item = {"name": name, "status": "BLOCKED", "error_type": type(error).__name__}
        item["ms"] = round(1000 * (time.perf_counter() - started), 2)
        report["model_initialization"].append(item)
        print(json.dumps(item), flush=True)
    cases = {c["id"]: c for c in load(ROOT / "evaluation/query_search/cases.json")["cases"]}
    plans = {
        variant: {r["id"]: r for r in load(PRIOR / filename)["rows"]}
        for variant, filename in [("B_deterministic", "deterministic.json"), ("C_gemini", "matched.json")]
    }
    schedule = []
    for case_id, focused in FOCUSED.items():
        variants = {"A_original": [cases[case_id]["question"]], "D_research_only": focused}
        for variant in plans:
            row = plans[variant][case_id]
            variants[variant] = [q["text"] for q in row["plan"]["subqueries"]] if row["status"] == "OK" else []
        for variant, queries in variants.items():
            schedule.extend((case_id, variant, i, query, "bm25") for i, query in enumerate(queries))
    for case_id in ("Q001", "Q004", "Q022"):
        query = plans["C_gemini"][case_id]["plan"]["subqueries"][0]["text"]
        schedule.extend((case_id, "C_gemini", 0, query, mode) for mode in ("dense", "hybrid", "rerank"))
    # Literal repeats reuse identical calls only within this run, recording aliases.
    cache = {}
    for case_id, variant, index, query, mode in schedule:
        key = (query, mode)
        row = {"id": case_id, "query_source": variant, "query_index": index, "query": query, "mode": mode}
        if key in cache:
            row.update(reused_observation=cache[key], latency_ms=None)
        else:
            started = time.perf_counter()
            plan = QueryPlan(
                original=cases[case_id]["question"],
                intent="legal_question",
                domain="unknown",
                temporal_scope=[],
                subqueries=[{"text": query, "purpose": "question_part"}],
                clarification=None,
            )
            try:
                result = await search(
                    plan.model_dump(),
                    reranked if mode == "rerank" else base,
                    SearchOptions(
                        mode="hybrid" if mode == "rerank" else mode,
                        top_k=10,
                        as_of_date="2026-11-23",
                        allowed_usage_policies=("EXPERIMENTAL_ONLY",),
                    ),
                    timeout_seconds=80,
                )
                row.update(
                    status=result["status"],
                    completeness=result["completeness"],
                    checks=checks(result, cases[case_id]),
                    requests=[r.model_dump(mode="json") for r in result["requests"]],
                    responses=[r.model_dump(mode="json") for r in result["responses"]],
                    evidence=[e.model_dump(mode="json") for e in result["evidence"]],
                    warnings=result["warnings"],
                    errors=[e.model_dump(mode="json") for e in result["errors"]],
                )
            except Exception as error:
                row.update(status="BLOCKED", error_type=type(error).__name__)
            row["latency_ms"] = round(1000 * (time.perf_counter() - started), 2)
            cache[key] = len(report["rows"])
        report["rows"].append(row)
        save(output / "experiments.json", report)
        print(
            json.dumps(
                {
                    k: row[k]
                    for k in ("id", "query_source", "mode", "status", "latency_ms", "reused_observation")
                    if k in row
                }
            ),
            flush=True,
        )
    save(output / "coverage_after.json", await metadata(base._sources._client))


async def coverage_probes(output):
    """Bounded substring probes, not semantic coverage or relevance labels."""
    path = output / "coverage_probes.json"
    if path.exists():
        raise ValueError("Preserve previous probes")
    env = {**{k: v for k, v in dotenv_values(ROOT / ".env").items() if v is not None}, **os.environ}
    service = create_retrieval_service(load_settings(environ=env).supabase)
    client = service._sources._client
    report = {
        "visibility": "CURRENT_CREDENTIAL_VISIBLE_ROWS_ONLY",
        "snapshot": False,
        "filters": "NONE: probes include all visible policies/dates, not just search eligibility",
        "literal_queries": [],
        "exact_identity": [],
    }
    for literal in [
        "đơn phương chấm dứt",
        "bảo lãnh",
        "ly hôn",
        "giao dịch dân sự",
        "điều kiện có hiệu lực",
        "không giao hàng",
        "mua bán đất",
        "45/2019/QH14",
        "nghĩa vụ trả nợ",
    ]:
        response = await asyncio.to_thread(
            lambda literal=literal: (
                client.table("retrieval_chunks")
                .select("id,source_document_id,node_id,chunk_key,content,content_sha256", count="exact")
                .ilike("content", "%" + literal + "%")
                .order("id")
                .limit(10)
                .execute()
            )
        )
        report["literal_queries"].append(
            {"literal": literal, "count": response.count, "returned_limit": 10, "rows": response.data}
        )
    for number in ["45/2019/QH14"]:
        response = await asyncio.to_thread(
            lambda: (
                client.table("source_documents")
                .select(SOURCE_FIELDS, count="exact")
                .eq("document_number", number)
                .limit(10)
                .execute()
            )
        )
        report["exact_identity"].append({"document_number": number, "count": response.count, "rows": response.data})
    save(path, report)
    print(
        json.dumps(
            {
                "probes": [{"literal": r["literal"], "count": r["count"]} for r in report["literal_queries"]],
                "identity_count": report["exact_identity"][0]["count"],
            }
        )
    )


def analyze(output):
    """Rebuild derived reviews/summaries from saved responses only; no network."""
    p = output
    # Analysis may refresh null templates, never erase a reviewer's annotations.
    for name in ("human_review.json", "experimental_review.json"):
        path = p / name
        if path.exists() and any(
            row.get("label") is not None or row.get("reviewer") or row.get("reason") for row in load(path)["rows"]
        ):
            raise ValueError("Preserve annotated reviews; choose a fresh output directory")
    pool = load(ROOT / "evaluation/query_search/semantic_v2/relevance/pool.json")
    runs = load(ROOT / "evaluation/query_search/semantic_v2/relevance/runs.json")
    review = build_review(pool, runs)
    for row in review["rows"]:
        run = next(r for r in runs if r["id"] == row["case_id"] and r["variant"] == row["query_source"])
        e = next(
            e for e in run["responses"][row["query_index"]]["evidence"] if e["retrieval_chunk_id"] == row["chunk_id"]
        )
        row["temporal_metadata"] = {
            k: e.get(k) for k in ["issued_on", "effective_from", "effective_to", "effect_status_reported"]
        }
    save(p / "human_review.json", review)
    markdown = [
        "# Human relevance review queue",
        "",
        "Reused57 rows. All labels null.0–3 rubric. Relevance alone does not establish legal applicability.",
        "Assistant-provisional observations remain in the previous separate file; not imported here.",
        "",
    ]
    for r in review["rows"]:
        markdown += [
            f"## {r['review_id']} | {r['case_id']} | {r['query_source']} | native rank {r['native_rank']}",
            "",
            "Question: " + r["question"],
            "",
            "Issue: " + json.dumps(r["legal_issue"], ensure_ascii=False),
            "",
            "Objective: " + json.dumps(r["search_objective"], ensure_ascii=False),
            "",
            "Query: " + r["query"],
            "",
            "Source: " + r["document_title"] + " | " + r["source_document_id"],
            "",
            "Provision: " + json.dumps(r["provision_identity"], ensure_ascii=False),
            "",
            "Mode: " + r["retrieval_mode"] + " | chunk " + r["chunk_id"],
            "",
            "Temporal: " + json.dumps(r["temporal_metadata"], ensure_ascii=False),
            "",
            "```text",
            r["chunk_text"],
            "```",
            "",
            "Label: null | Reviewer: null | Reason: null",
            "",
        ]
    (p / "HUMAN_REVIEW_QUEUE.md").write_text("\n".join(markdown), encoding="utf-8")

    replays = []
    for run in runs:
        if "responses" not in run:
            replays.append({"id": run["id"], "variant": run["variant"], "status": "BLOCKED_QUERY_PLAN"})
            continue
        requests = [RetrievalRequest.model_validate(x) for x in run["requests"]]
        responses = [RetrievalResponse.model_validate(x) for x in run["responses"]]
        plan = QueryPlan.model_validate(run["plan"]).model_dump()
        result = _finish(plan, requests, responses, total=len(plan["subqueries"]), calls=len(requests))
        observation = {**run, "evidence": [x.model_dump(mode="json") for x in result["evidence"]]}
        replays.append(
            {
                "id": run["id"],
                "variant": run["variant"],
                "kind": "SAVED_NATIVE_RESPONSES_FINAL_SEARCH_FINISH_NO_NETWORK",
                "status": result["status"],
                "warnings": result["warnings"],
                "audit": inspect_native(observation),
            }
        )
    save(p / "current_search_replay.json", replays)

    d = load(p / "experiments.json")
    rows = []
    all_chunks = []
    for i, r in enumerate(d["rows"]):
        observed = d["rows"][r["reused_observation"]] if "reused_observation" in r else r
        e = observed["responses"][0]["evidence"] if observed.get("responses") else []
        rows.append(
            {
                "row": i,
                "id": r["id"],
                "variant": r["query_source"],
                "query_index": r["query_index"],
                "query": r["query"],
                "query_chars": len(r["query"]),
                "mode": r["mode"],
                "status": observed["status"],
                "reused_observation": r.get("reused_observation"),
                "latency_ms": r["latency_ms"],
                "prefix_ids": {str(k): [x["retrieval_chunk_id"] for x in e[:k]] for k in [3, 5, 10]},
                "rank_one_source": e[0]["title"] if e else None,
                "cross_reference_rank": next(
                    (x["rank"] for x in e if x["retrieval_chunk_id"] == "2973a693-2276-4e4f-a233-f7038e4717e0"), None
                ),
                "reranking_status": observed["responses"][0].get("reranking", {}).get("status") if e else None,
            }
        )
        if "reused_observation" not in r:
            for evidence in e:
                all_chunks.append(
                    {
                        "experiment_row": i,
                        "case_id": r["id"],
                        "query_source": r["query_source"],
                        "query": r["query"],
                        "mode": r["mode"],
                        "top_k": 10,
                        "native_rank": evidence["rank"],
                        "evidence": evidence,
                        "label": None,
                        "reviewer": None,
                        "reason": None,
                        "label_source": "unlabeled",
                    }
                )
    save(p / "experimental_review.json", {"expert_metrics": None, "rows": all_chunks})
    summary = {
        "scheduled_rows": len(rows),
        "executed_search_calls": sum("responses" in r for r in d["rows"]),
        "literal_reuses": sum("reused_observation" in r for r in d["rows"]),
        "completed_calls": sum(r.get("status") == "COMPLETED" for r in d["rows"]),
        "new_gemini_calls": 0,
        "existing_human_queue_rows": len(review["rows"]),
        "experimental_review_rows": len(all_chunks),
        "human_labels": 0,
        "same_observed_metadata_before_after": load(p / "coverage.json") == load(p / "coverage_after.json"),
        "model_initialization": d["model_initialization"],
        "latency_by_mode_ms": {
            m: {
                "n": len(t := [r["latency_ms"] for r in rows if r["mode"] == m and r["latency_ms"] is not None]),
                "median": median(t),
                "min": min(t),
                "max": max(t),
            }
            for m in ["bm25", "dense", "hybrid", "rerank"]
        },
        "rows": rows,
    }
    save(p / "experiment_summary.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation/query_search/relevance_investigation")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--analyze-only", action="store_true")
    mode.add_argument("--coverage-probes-only", action="store_true")
    args = parser.parse_args()
    if args.analyze_only:
        analyze(args.output)
        return
    if args.coverage_probes_only:
        asyncio.run(coverage_probes(args.output))
        return
    if args.output.exists():
        raise ValueError("Preserve previous investigation; choose a fresh output directory")
    args.output.mkdir(parents=True)
    offline(args.output)
    if args.live:
        asyncio.run(live(args.output))


if __name__ == "__main__":
    main()
