"""Matched semantic evaluation with a persistent task-wide Gemini request budget."""

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from scripts.evaluate_query_search import aggregate, evaluate, score
from src.applications.tillegal.agents.query.agent import understand
from src.applications.tillegal.agents.query.semantic import SemanticQueryAgent
from src.framework.llm.providers import gemini_adapter

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "evaluation/query_search/semantic_v2"
DEFAULT_IDS = ",".join([f"Q{index:03}" for index in range(1, 46, 3)] + ["Q005", "Q044", "Q006", "Q018", "Q042"])


def failure_inclusive(rows: list[dict], cases: dict) -> dict:
    successful = [row for row in rows if row["status"] == "OK"]
    keys = [
        ("issue_matches", "issue_total", "expected_issues"),
        ("distinct_objective_matches", "issue_total", "expected_issues"),
        ("fact_matches", "fact_total", "expected_preserved_facts"),
        ("missing_info_matches", "missing_info_total", "required_missing_information"),
        ("temporal_matches", "temporal_total", "temporal_expectations"),
        ("citation_matches", "citation_total", "citation_constraints"),
    ]
    result = {"cases": len(rows), "accepted": len(successful), "failures": len(rows) - len(successful)}
    for numerator, _, ground_truth in keys:
        denominator = sum(len(cases[row["id"]][ground_truth]) for row in rows)
        count = sum(row["metrics"][numerator] for row in successful)
        result[numerator] = {
            "numerator": count,
            "denominator": denominator,
            "ratio": round(count / denominator, 4) if denominator else None,
        }
    result["note"] = "Same authored rules. Failed plans contribute zero; semantic metrics remain heuristic."
    return result


async def run(args):
    FOLDER.mkdir(exist_ok=True)
    budget_path = FOLDER / "api_budget.json"
    budget = (
        json.loads(budget_path.read_text(encoding="utf-8")) if budget_path.exists() else {"maximum": 25, "attempted": 0}
    )
    if args.mode == "gemini":
        requested = len(args.ids.split(","))
        if requested > budget["maximum"] - budget["attempted"]:
            raise ValueError("SEMANTIC_EVALUATION_BUDGET_INSUFFICIENT")
    original = gemini_adapter._acompletion

    async def limited(**kwargs):
        if budget["attempted"] >= budget["maximum"]:
            raise RuntimeError("SEMANTIC_EVALUATION_BUDGET_EXHAUSTED")
        budget["attempted"] += 1
        budget_path.write_text(json.dumps(budget, indent=2) + "\n", encoding="utf-8")
        return await original(**kwargs)

    with patch.object(gemini_adapter, "_acompletion", limited):
        result = await evaluate(args)
    cases = {
        case["id"]: case
        for case in json.loads((ROOT / "evaluation/query_search/cases.json").read_text(encoding="utf-8"))["cases"]
    }
    result["failure_inclusive"] = failure_inclusive(result["rows"], cases)
    result["source_hashes"] = {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in [
            "src/applications/tillegal/agents/query/agent.py",
            "src/applications/tillegal/agents/query/context.py",
            "src/applications/tillegal/agents/query/semantic.py",
            "src/applications/tillegal/agents/query/prompts.py",
            "src/applications/tillegal/agents/query/schemas.py",
        ]
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["failure_inclusive"]))


async def replay():
    rows = []
    for name in ["gemini-before.json", "gemini-after.json", "gemini-final.json"]:
        old = json.loads((ROOT / "evaluation/query_search/runs" / name).read_text(encoding="utf-8"))
        for row in old["rows"]:
            if row.get("raw_response") is None:
                continue

            async def complete(**kwargs):
                return row["raw_response"]

            record = {
                "run": name,
                "id": row["id"],
                "historical_status": row["status"],
                "execution": "SAVED_RAW_REPLAY_NO_API",
            }
            try:
                record.update(
                    status="OK",
                    plan=await SemanticQueryAgent(complete, "recorded-response").understand(row["question"]),
                )
            except Exception as error:
                record.update(status="ERROR", error_type=type(error).__name__)
            rows.append(record)
    path = FOLDER / "raw_replay.json"
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"replayed": len(rows), "api_calls": 0}))


async def summarize():
    reports = [
        json.loads((FOLDER / name).read_text(encoding="utf-8")) for name in ["gemini.json", "gemini-resume.json"]
    ]
    cases = {
        case["id"]: case
        for case in json.loads((ROOT / "evaluation/query_search/cases.json").read_text(encoding="utf-8"))["cases"]
    }
    history = {}
    for report in reports:
        for row in report["rows"]:
            history.setdefault(row["id"], []).append(row)
    rows = []
    for case_id, attempts in history.items():
        saved = attempts[-1]
        row = {
            **saved,
            "attempt_history": [
                {"status": item["status"], "error": item.get("error"), "api_calls": item["api_calls"]}
                for item in attempts
            ],
            "original_api_plan_status": saved["status"],
            "postprocessing": "SAVED_RAW_FINAL_CODE_REPLAY_NO_API",
        }
        if saved.get("raw_response"):

            async def complete(**kwargs):
                return saved["raw_response"]

            try:
                plan = await SemanticQueryAgent(complete, reports[-1]["model"]).understand(cases[case_id]["question"])
                row.update(status="OK", plan=plan, metrics=score(cases[case_id], plan))
                row.pop("error", None)
            except Exception as error:
                row.update(status="ERROR", error={"code": str(error), "type": type(error).__name__})
        elif saved["api_calls"] == 0:
            plan = understand(cases[case_id]["question"])
            row.update(status="OK", plan=plan, metrics=score(cases[case_id], plan))
        rows.append(row)
    baseline = json.loads((ROOT / "evaluation/query_search/runs/gemini-before.json").read_text(encoding="utf-8"))
    ids = {row["id"] for row in baseline["rows"]}
    matched = [row for row in rows if row["id"] in ids]
    result = {
        "schema_version": "1",
        "mode": "gemini",
        "model": reports[0]["model"],
        "prompt_sha256": reports[0]["prompt_sha256"],
        "prompt_text": reports[0]["prompt_text"],
        "dataset_sha256": reports[0]["dataset_sha256"],
        "execution": "REAL_GEMINI_RESPONSES_REPLAYED_THROUGH_FINAL_POSTPROCESSING",
        "rows": rows,
        "aggregate": aggregate(rows),
        "failure_inclusive": failure_inclusive(rows, cases),
        "matched_baseline_ids": sorted(ids),
        "matched_final": failure_inclusive(matched, cases),
        "matched_historical_baseline": failure_inclusive(baseline["rows"], cases),
        "first_attempt_accepted": sum(attempts[0]["status"] == "OK" for cid, attempts in history.items() if cid in ids),
        "attempted_api_calls_all_batches": sum(row["api_calls"] for report in reports for row in report["rows"]),
        "source_hashes": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in reports[0]["source_hashes"]
        },
    }
    (FOLDER / "matched.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                key: result[key]
                for key in [
                    "matched_final",
                    "matched_historical_baseline",
                    "first_attempt_accepted",
                    "attempted_api_calls_all_batches",
                ]
            }
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("deterministic", "gemini", "replay", "summarize"), required=True)
    parser.add_argument("--ids", default=DEFAULT_IDS)
    parser.add_argument("--label", default="semantic-v2")
    parser.add_argument("--max-requests", type=int, default=20)
    parser.add_argument("--output", type=Path, default=FOLDER / "gemini.json")
    args = parser.parse_args()
    if args.mode == "replay":
        asyncio.run(replay())
    elif args.mode == "summarize":
        asyncio.run(summarize())
    else:
        asyncio.run(run(args))


if __name__ == "__main__":
    main()
