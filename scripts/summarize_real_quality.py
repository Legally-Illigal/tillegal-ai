"""Compare operational/model-verdict outcomes, never human legal accuracy."""

import argparse
import json
from collections import Counter
from pathlib import Path

from src.applications.tillegal.evaluation.quality_metrics import percentile


def category(row):
    result = row["result"]
    if result["status"] == "FAILED":
        return "generation_or_runtime:" + result.get("error", "UNKNOWN")
    if result.get("claims"):
        return "published_experimental_draft"
    judges = result.get("judgments", [])
    if not judges or not judges[-1]["selected"]:
        if not any(b["evidence"] for b in result.get("evidence_bundles", [])):
            return "no_retrieved_evidence"
        return "context_or_judge_abstention"
    if not result.get("citation_checks"):
        return "model_abstention"
    return "verification_or_publication_rejection"


def summarize(root):
    rows = [json.loads(p.read_text(encoding="utf8")) for p in sorted(root.glob("*.json")) if p.name != "manifest.json"]
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf8"))
    expected = {
        (p, c["id"])
        for p in manifest.get("policies", ["legacy", "context", "context_judge"])
        for c in manifest["cases"]
    }
    if len(rows) != len(expected) or {(r["policy"], r["id"]) for r in rows} != expected:
        raise ValueError("Experiment is incomplete or has duplicate cases")
    summary = {}
    for policy in sorted({r["policy"] for r in rows}):
        subset = [r for r in rows if r["policy"] == policy]
        calls = [c for r in subset for c in r["provider_calls"]]
        usage = {
            key: sum(c.get("usage", {}).get(key, 0) for c in calls) for key in ("prompt_tokens", "completion_tokens")
        }
        summary[policy] = {
            "execution": manifest.get("execution", "live_local"),
            "latency_scope": "replay_without_inference"
            if manifest.get("execution") == "frozen_real_completions_replay"
            else "live_end_to_end",
            "usage_origin": "prior_recorded_requests"
            if manifest.get("execution") == "frozen_real_completions_replay"
            else "current_requests",
            "distinct_cases": len(subset),
            "outcomes": dict(Counter(category(r) for r in subset)),
            "p50_ms": percentile([r["elapsed_ms"] for r in subset], 0.5),
            "p95_ms": percentile([r["elapsed_ms"] for r in subset], 0.95),
            "reported_tokens_partial": usage,
            "usage_complete": all("usage" in c for c in calls),
            "publication_blockers": dict(
                Counter(
                    c["publication_blocker"]
                    for r in subset
                    for c in r["result"].get("citation_checks", [])
                    if c.get("publication_blocker")
                )
            ),
            "model_verdicts": dict(
                Counter(c["claim_support"] for r in subset for c in r["result"].get("citation_checks", []))
            ),
            "human_correctness": None,
            "condition_exception_coverage": None,
        }
    return rows, summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    manifests = [json.loads((r / "manifest.json").read_text(encoding="utf8")) for r in (args.before, args.after)]
    for key in ("cases", "weights_sha256", "model_revision", "index_sha256", "retrieval", "workflow"):
        if manifests[0][key] != manifests[1][key]:
            raise ValueError("Unpaired experiment: " + key)
    before, b = summarize(args.before)
    after, a = summarize(args.after)
    lookup = {(r["policy"], r["id"]): r for r in before}
    if set(lookup) != {(r["policy"], r["id"]) for r in after}:
        raise ValueError("Missing paired cases")
    paired = [
        {"policy": r["policy"], "id": r["id"], "before": category(lookup[r["policy"], r["id"]]), "after": category(r)}
        for r in after
    ]
    with args.output.open("x", encoding="utf8") as f:
        json.dump(
            {
                "classification": "exploratory_no_gold",
                "before": b,
                "after": a,
                "pairs": paired,
                "warning": "Published drafts and model verdicts are not legal correctness.",
            },
            f,
            indent=2,
        )
    print(json.dumps({"before": b, "after": a}, indent=2))
