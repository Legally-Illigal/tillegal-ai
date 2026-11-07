"""Summarize exploratory A/B/C measurements without assigning legal quality labels."""

import json
from pathlib import Path

from src.applications.tillegal.evaluation.quality_metrics import percentile


def summarize(root):
    reports = {
        name: json.loads((root / (name + ".json")).read_text(encoding="utf8"))
        for name in ("before", "legacy", "context", "context_judge")
    }
    before = reports["before"]
    for name, report in reports.items():
        if (
            report["dataset_sha256"] != before["dataset_sha256"]
            or report["index_manifest_sha256"] != before["index_manifest_sha256"]
            or report["retrieval"] != before["retrieval"]
        ):
            raise ValueError("Unpaired experiment")
    result = {}
    for name, report in reports.items():
        rows = report["rows"]
        timings = {
            "end_to_end": [r["elapsed_ms"] for r in rows],
            "retrieval": [r["retrieval_ms"] for r in rows],
            "context": [sum(t.get("context_ms", 0) for t in r["stage_timings"]) for r in rows],
            "judge": [
                sum(t["elapsed_ms"] - t.get("context_ms", 0) for t in r["stage_timings"])
                for r in rows
                if r["stage_timings"]
            ],
        }
        result[name] = {
            "samples": len(rows),
            "unique_questions": len({r["case"] for r in rows}),
            "timings_ms": {
                stage: {"p50": percentile(values, 0.5), "p95": percentile(values, 0.95)}
                for stage, values in timings.items()
            },
            "calls": sum(r["calls"] for r in rows),
            "abstentions": sum(r["status"] == "ABSTAINED" for r in rows),
            "refinements": sum(len(r["judge"]) - 1 for r in rows),
            "context_selected_counts": [len(r["selected"]) for r in rows if r["repeat"] == 0],
            "legal_quality": None,
            "memory_bytes": None,
            "tokens": None,
            "estimated_cost": None,
            "confidence_interval": None,
        }
    # Same legacy policy before/after must keep stable selected identities and call counts.
    fields = ("selected", "calls", "status", "selected_evidence")
    if len(before["rows"]) != len(reports["legacy"]["rows"]):
        raise ValueError("Mismatched number of baseline observations")
    result["legacy_parity"] = all(
        all(old[f] == new[f] for f in fields) for old, new in zip(before["rows"], reports["legacy"]["rows"])
    )
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1] / ".docs/development/m4-results"
    result = summarize(root)
    with (root / "summary.json").open("x", encoding="utf8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))
