"""Balanced real-corpus relevance review pool. Labels are never inferred from hits."""

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path

from dotenv import dotenv_values

from scripts.evaluate_query_search_retrieval import checks, sanitize
from src.applications.tillegal.agents.query.agent import QueryPlan
from src.applications.tillegal.agents.search.agent import SearchOptions, search
from src.core.config import load_settings
from src.retrieval_bootstrap import create_retrieval_service

ROOT = Path(__file__).resolve().parents[1]
CASES = ["Q001", "Q004", "Q005", "Q007", "Q019", "Q022", "Q025", "Q040"]
RUBRIC = {
    "0": "Unrelated to this information need",
    "1": "Broadly related, insufficiently targeted",
    "2": "Relevant to part of this information need",
    "3": "Directly relevant to this objective",
}


def label_status(rows: list[dict], labels: list[dict]) -> dict:
    known = {row["review_id"] for row in rows}
    seen = set()
    counts = {"human_reviewed": 0, "model_assisted_provisional": 0, "automatic_proxy": 0, "unlabeled": 0}
    for item in labels:
        if item["review_id"] not in known or item["review_id"] in seen:
            raise ValueError("Unknown or duplicate review identifier")
        seen.add(item["review_id"])
        label = item.get("label")
        source = item.get("label_source", "unlabeled")
        if label is None:
            counts["unlabeled"] += 1
        elif type(label) is not int or not 0 <= label <= 3 or source not in counts or source == "unlabeled":
            raise ValueError("A score requires integer 0..3 and explicit review provenance")
        elif not item.get("reviewer") or not item.get("reason"):
            raise ValueError("A score requires reviewer identity and reason")
        else:
            counts[source] += 1
    counts["unlabeled"] += len(known - seen)
    return {
        "counts": counts,
        "expert_precision_at_k": None,
        "expert_recall_at_k": None,
        "expert_ndcg": None,
        "note": "No expert ground truth/corpus relevance coverage established; never turn null labels into zero.",
    }


async def collect(args):
    if args.output.exists():
        raise ValueError("Preserve previous relevance run; choose a new folder")
    args.output.mkdir(parents=True)
    cases = {
        item["id"]: item
        for item in json.loads((ROOT / "evaluation/query_search/cases.json").read_text(encoding="utf-8"))["cases"]
    }
    files = {"deterministic": args.deterministic, "gemini": args.gemini}
    inputs = {
        variant: {row["id"]: row for row in json.loads(path.read_text(encoding="utf-8"))["rows"]}
        for variant, path in files.items()
    }
    env = {**{key: value for key, value in dotenv_values(ROOT / ".env").items() if value is not None}, **os.environ}
    service = create_retrieval_service(load_settings(environ=env).supabase, timeout_seconds=30)
    pool, runs, index_signatures = [], [], set()
    for case_id in CASES:
        as_of = "2010-12-31" if case_id == "Q019" else "2026-11-23"
        # Historical anchor is an explicit evaluation setting, not inferred from year.
        options = SearchOptions(mode="bm25", top_k=3, as_of_date=as_of, allowed_usage_policies=("EXPERIMENTAL_ONLY",))
        for variant in ("deterministic", "gemini"):
            source = inputs[variant].get(case_id)
            observation = {"id": case_id, "variant": variant, "search_options": options.model_dump(mode="json")}
            if source is None or source["status"] != "OK":
                runs.append(
                    {
                        **observation,
                        "status": "BLOCKED_QUERY_PLAN",
                        "source_error": source.get("error") if source else None,
                    }
                )
                continue
            plan = QueryPlan.model_validate(source["plan"]).model_dump()
            result = await search(plan, service, options)
            validated = checks(result, cases[case_id])
            # Technical checks are not a relevance metric.
            validated.pop("objective_topic_matches_proxy", None)
            validated.pop("objective_topic_total", None)
            validated.pop("relevance_assessment", None)
            links = {item["query_index"]: item["issue_indices"] for item in plan.get("search_objectives", [])}
            observation.update(
                status=result["status"],
                completeness=result["completeness"],
                checks=validated,
                plan=plan,
                requests=[item.model_dump(mode="json") for item in result["requests"]],
                responses=[item.model_dump(mode="json") for item in result["responses"]],
                evidence=[item.model_dump(mode="json") for item in result["evidence"]],
                warnings=list(result["warnings"]),
                errors=[item.model_dump(mode="json") for item in result["errors"]],
            )
            for query_index, response in enumerate(result["responses"]):
                if response.index:
                    index_signatures.add(response.index.model_dump_json())
                for item in response.evidence:
                    identity = f"{case_id}/{variant}/{query_index}/{item.retrieval_chunk_id}/{item.content_sha256}"
                    pool.append(
                        {
                            "review_id": hashlib.sha256(identity.encode()).hexdigest()[:20],
                            "case_id": case_id,
                            "question": cases[case_id]["question"],
                            "issue_labels": [plan["issues"][index] for index in links.get(query_index, [])],
                            "search_objective": response.query,
                            "query_index": query_index,
                            "rank": item.rank,
                            "document_title": item.title,
                            "source_url": item.source_url,
                            "provision_identity": {
                                "chunk_key": item.chunk_key,
                                "node_id": item.node_id,
                                "block_id": item.block_id,
                            },
                            "chunk_id": str(item.retrieval_chunk_id),
                            "source_document_id": str(item.source_document_id),
                            "source_snapshot_id": item.source_snapshot_id,
                            "content_sha256": item.content_sha256,
                            "chunk_text": item.content,
                            "label": None,
                            "label_source": "unlabeled",
                            "reviewer": None,
                            "reason": None,
                            "blind_variant_token": hashlib.sha256(variant.encode()).hexdigest()[:8],
                        }
                    )
            runs.append(observation)
            (args.output / "runs.json").write_text(
                json.dumps(sanitize(runs), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            print(
                json.dumps(
                    {"id": case_id, "variant": variant, "status": result["status"], "evidence": len(result["evidence"])}
                ),
                flush=True,
            )
    report = {
        "rubric": RUBRIC,
        "mode": "bm25",
        "top_k": 3,
        "questions": CASES,
        "index_signatures": sorted(index_signatures),
        "same_observed_index_identity": len(index_signatures) == 1,
        "consistency": "BEST_EFFORT_NO_TRANSACTION_SNAPSHOT",
        "historical_date_note": "Q019 uses explicit2010-12-31 evaluation anchor; no applicability inferred.",
        "rows": pool,
        "label_status": label_status(pool, []),
    }
    (args.output / "pool.json").write_text(
        json.dumps(sanitize(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    labels = [{key: row[key] for key in ("review_id", "label", "label_source", "reviewer", "reason")} for row in pool]
    (args.output / "labels_template.json").write_text(
        json.dumps(labels, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    review = [
        "# Relevance review queue",
        "",
        "Rubric 0–3, relevance only; no legal applicability/correctness claim.",
        "Edit labels_template.json, retaining review_id; identify reviewer/source and explain every score.",
        "No expert labels currently available; null is unreviewed, not relevance zero.",
        "",
    ]
    for row in pool:
        review += [
            f"## {row['review_id']} / {row['case_id']} / rank {row['rank']}",
            "",
            row["question"],
            "",
            "Issues: " + json.dumps(row["issue_labels"], ensure_ascii=False),
            "",
            "Objective: " + row["search_objective"],
            "",
            "Source: " + row["document_title"],
            "",
            "Identity: " + json.dumps(row["provision_identity"], ensure_ascii=False),
            "",
            "```text",
            row["chunk_text"],
            "```",
            "",
        ]
    (args.output / "REVIEW_QUEUE.md").write_text("\n".join(review), encoding="utf-8")
    print(
        json.dumps(
            {
                "review_rows": len(pool),
                "labels": report["label_status"],
                "index_stable": report["same_observed_index_identity"],
            }
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gemini", type=Path, required=True)
    parser.add_argument(
        "--deterministic", type=Path, default=ROOT / "evaluation/query_search/runs/deterministic-before.json"
    )
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation/query_search/semantic_v2/relevance")
    asyncio.run(collect(parser.parse_args()))


if __name__ == "__main__":
    main()
