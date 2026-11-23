"""Reproducible Query understanding evaluation; heuristic scores are not legal judgments."""

import argparse
import asyncio
import hashlib
import json
import re
import statistics
import time
import unicodedata
from collections import Counter
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from src.applications.tillegal.agents.query.agent import QueryPlan, understand
from src.applications.tillegal.agents.query.gemini import create_gemini_query_agent
from src.applications.tillegal.agents.query.prompts import SYSTEM_PROMPT
from src.applications.tillegal.agents.query.schemas import SemanticAnalysis
from src.framework.llm.providers import gemini_adapter

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "evaluation/query_search/cases.json"


def matches(pattern: str, text: str) -> bool:
    text = unicodedata.normalize("NFC", text).casefold()
    return any(re.search(r"(?<!\w)" + re.escape(term.casefold()) + r"(?!\w)", text) for term in pattern.split("|"))


def objective_assignment(expected: list[str], queries: list[str]) -> int:
    """Maximum distinct objectives matched to distinct queries; max four queries."""

    def visit(index, used):
        if index == len(expected):
            return 0
        return max(
            [visit(index + 1, used)]
            + [
                1 + visit(index + 1, used | {j})
                for j, text in enumerate(queries)
                if j not in used and matches(expected[index], text)
            ]
        )

    return visit(0, set())


def score(case: dict, plan: dict) -> dict:
    queries = [item["text"] for item in plan["subqueries"]]
    issue_text = " ".join(plan["issues"] + queries)
    facts_text = " ".join(item["text"] for item in plan["facts"])
    missing_text = " ".join(plan["missing_information"] + ([plan["clarification"]] if plan["clarification"] else []))
    all_citations = " ".join(queries)
    expected = case["expected_issues"]
    return {
        "schema_valid": True,
        "original_preserved": plan["original"] == case["question"],
        "intent_correct": plan["intent"] == case["expected_intent"],
        "issue_matches": sum(matches(item, issue_text) for item in expected),
        "issue_total": len(expected),
        "distinct_objective_matches": objective_assignment(expected, queries),
        "unmatched_issue_labels": sum(not any(matches(item, label) for item in expected) for label in plan["issues"]),
        "fact_matches": sum(item in facts_text for item in case["expected_preserved_facts"]),
        "fact_total": len(case["expected_preserved_facts"]),
        "ungrounded_fact_spans": sum(
            item["text"] not in unicodedata.normalize("NFC", case["question"]) for item in plan["facts"]
        ),
        "forbidden_claim_matches": sum(item in issue_text + facts_text for item in case["forbidden_invented_facts"]),
        "missing_info_matches": sum(matches(item, missing_text) for item in case["required_missing_information"]),
        "missing_info_total": len(case["required_missing_information"]),
        "redundant_missing_topics": [item for item in case["already_supplied_topics"] if matches(item, missing_text)],
        "clarification_correct": bool(plan["clarification"]) == case["clarification_expected"],
        "temporal_matches": sum(
            any(item in mention for mention in plan["temporal_scope"]) for item in case["temporal_expectations"]
        ),
        "temporal_total": len(case["temporal_expectations"]),
        "citation_matches": sum(item.casefold() in all_citations.casefold() for item in case["citation_constraints"]),
        "citation_total": len(case["citation_constraints"]),
        "unique_queries": len(set(queries)) == len(queries),
        "subquery_count": len(queries),
        "human_review_required": True,
    }


def aggregate(rows: list[dict]) -> dict:
    good = [row for row in rows if row["status"] == "OK"]
    metrics = [row["metrics"] for row in good]

    def ratio(numerator, denominator):
        total = sum(item[denominator] for item in metrics)
        return round(sum(item[numerator] for item in metrics) / total, 4) if total else None

    latencies = sorted(row["latency_ms"] for row in rows)
    return {
        "cases": len(rows),
        "successes": len(good),
        "failures": len(rows) - len(good),
        "schema_valid_plans": sum(item["schema_valid"] for item in metrics),
        "raw_schema_valid_responses": sum(row.get("raw_schema_valid") is True for row in rows),
        "live_model_calls": sum(row.get("api_calls", 0) for row in rows),
        "analysis_methods": dict(Counter(row["plan"]["analysis_method"] for row in good)),
        "issue_coverage_proxy": ratio("issue_matches", "issue_total"),
        "distinct_objective_proxy": ratio("distinct_objective_matches", "issue_total"),
        "fact_span_coverage": ratio("fact_matches", "fact_total"),
        "missing_information_proxy": ratio("missing_info_matches", "missing_info_total"),
        "temporal_span_coverage": ratio("temporal_matches", "temporal_total"),
        "citation_identity_coverage": ratio("citation_matches", "citation_total"),
        "redundant_missing_case_count": sum(bool(item["redundant_missing_topics"]) for item in metrics),
        "unmatched_issue_labels_proxy": sum(item["unmatched_issue_labels"] for item in metrics),
        "ungrounded_fact_spans": sum(item["ungrounded_fact_spans"] for item in metrics),
        "clarification_correct_cases": sum(item["clarification_correct"] for item in metrics),
        "intent_correct_cases": sum(item["intent_correct"] for item in metrics),
        "errors": dict(Counter(row["error"]["code"] for row in rows if row.get("error"))),
        "latency_ms": {
            "median": round(statistics.median(latencies), 2),
            "p95_nearest_rank": latencies[max(0, (95 * len(latencies) + 99) // 100 - 1)],
        }
        if rows
        else {},
        "tokens": {
            key: sum(row.get("usage", {}).get(key, 0) or 0 for row in rows)
            for key in ("prompt_tokens", "completion_tokens", "total_tokens")
        },
        "cost_usd": None,
        "cost_note": "No independently verified price/account billing data; no estimated cost claimed.",
        "semantic_grade": "HEURISTIC_REQUIRES_HUMAN_REVIEW",
    }


async def evaluate(args: argparse.Namespace) -> dict:
    cases = json.loads(DATASET.read_text(encoding="utf-8"))["cases"]
    if args.mode == "gemini" and not args.ids:
        cases = [case for case in cases if case["live_sample"]]
    if args.ids:
        wanted = set(args.ids.split(","))
        cases = [case for case in cases if case["id"] in wanted]
    if args.mode == "gemini" and len(cases) > args.max_requests:
        raise ValueError("Sample exceeds explicit maximum request budget")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise ValueError("Result file already exists; preserve prior runs")
    agent = create_gemini_query_agent() if args.mode == "gemini" else None
    report = {
        "schema_version": "1",
        "mode": args.mode,
        "label": args.label,
        "model": agent.model if agent else None,
        "timeout_seconds": agent.timeout_seconds if agent else None,
        "dataset_sha256": hashlib.sha256(DATASET.read_bytes()).hexdigest(),
        "prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
        "prompt_text": SYSTEM_PROMPT,
        "execution": "sequential",
        "maximum_requests": args.max_requests,
        "rows": [],
    }
    original_completion = gemini_adapter._acompletion
    for case in cases:
        started = time.perf_counter()
        row = {
            "id": case["id"],
            "category": case["category"],
            "split": case["split"],
            "question": case["question"],
            "api_calls": 0,
            "usage": {},
            "raw_response": None,
        }

        async def observed_sdk(**kwargs):
            row["api_calls"] += 1
            response = await original_completion(**kwargs)
            usage = getattr(response, "usage", None)
            row["usage"] = {
                name: getattr(usage, name, None) for name in ("prompt_tokens", "completion_tokens", "total_tokens")
            }
            row["provider_model"] = getattr(response, "model", None)
            return response

        async def recorded(**kwargs):
            raw = await agent.complete(**kwargs)
            row["raw_response"] = raw
            try:
                SemanticAnalysis.model_validate_json(raw)
                row["raw_schema_valid"] = True
            except ValueError:
                row["raw_schema_valid"] = False
            return raw

        try:
            with patch.object(gemini_adapter, "_acompletion", observed_sdk):
                plan = (
                    await replace(agent, complete=recorded).understand(case["question"])
                    if agent
                    else understand(case["question"])
                )
            plan = QueryPlan.model_validate(plan).model_dump()
            row.update(status="OK", plan=plan, metrics=score(case, plan))
        except Exception as error:
            from scripts.verify_gemini_query import safe_error

            row.update(status="ERROR", error=safe_error(error))
        row["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
        report["rows"].append(row)
        report["aggregate"] = aggregate(report["rows"])
        report["by_category"] = {
            category: aggregate([r for r in report["rows"] if r["category"] == category])
            for category in sorted({r["category"] for r in report["rows"]})
        }
        # Write after each case so interrupted runs never lose the completed subset.
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    "id": row["id"],
                    "status": row["status"],
                    "ms": row["latency_ms"],
                    "api_calls": row["api_calls"],
                    "error": row.get("error"),
                }
            ),
            flush=True,
        )
        if (
            row.get("error", {}).get("http_status") == 429
            or row.get("error", {}).get("provider_code") == "GEMINI_RATE_LIMITED"
        ):
            report["stopped_reason"] = "RATE_LIMIT_NO_RETRY"
            break
        if args.mode == "gemini" and row["api_calls"]:
            await asyncio.sleep(0.5)
    report["aggregate"] = aggregate(report["rows"])
    report["selected_cases"] = [case["id"] for case in cases]
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("deterministic", "gemini"), required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-requests", type=int, default=15)
    parser.add_argument("--ids", help="Optional comma-separated fixed IDs for paired investigations")
    args = parser.parse_args()
    if not 1 <= args.max_requests <= 30:
        parser.error("max-requests must be 1..30")
    result = asyncio.run(evaluate(args))
    print(json.dumps(result["aggregate"], ensure_ascii=True))


if __name__ == "__main__":
    main()
