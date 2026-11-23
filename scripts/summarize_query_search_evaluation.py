"""Recompute comparison metrics from immutable saved runs; no provider/database calls."""

import json
from pathlib import Path

from scripts.evaluate_query_search import aggregate

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "evaluation/query_search"


def load(name: str) -> dict:
    return json.loads((DATA / "runs" / name).read_text(encoding="utf-8"))


def main() -> None:
    a, b, candidate, final = [
        load(name)
        for name in ("deterministic-before.json", "gemini-before.json", "gemini-after.json", "gemini-final.json")
    ]
    baseline_ids = {row["id"] for row in b["rows"]}
    final_ids = {row["id"] for row in final["rows"]}
    paired_final_ids = baseline_ids & final_ids
    a15 = aggregate([row for row in a["rows"] if row["id"] in baseline_ids])
    candidate15 = aggregate([row for row in candidate["rows"] if row["id"] in baseline_ids])
    before5 = aggregate([row for row in b["rows"] if row["id"] in paired_final_ids])
    final5 = aggregate([row for row in final["rows"] if row["id"] in paired_final_ids])
    summary = {
        "deterministic_45": a["aggregate"],
        "deterministic_matched_15": a15,
        "gemini_baseline_15": b["aggregate"],
        "rejected_candidate_matched_15": candidate15,
        "final_6": final["aggregate"],
        "paired_final_ids": sorted(paired_final_ids),
        "baseline_paired_final": before5,
        "final_paired": final5,
        "total_attempted_gemini_calls": sum(run["aggregate"]["live_model_calls"] for run in (b, candidate, final)),
        "observed_tokens": sum(run["aggregate"]["tokens"]["total_tokens"] for run in (b, candidate, final)),
        "deterministic_before_after_identical": [row["plan"] for row in a["rows"]]
        == [row["plan"] for row in load("deterministic-after.json")["rows"]],
    }
    (DATA / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Updated evaluation/query_search/summary.json from saved runs; no API calls.")


if __name__ == "__main__":
    main()
