"""Extend the pinned T5 evaluator with binary nDCG and retrieval timing."""
import argparse
import hashlib
import json
from math import log2
from pathlib import Path
from statistics import mean, median

from ai_core.retrieval_evaluation import evaluate


def binary_ndcg(ranked, relevant, k):
    if k < 1 or not relevant or len(set(ranked)) != len(ranked):
        raise ValueError("Expected positive cutoff, relevant units and unique ranked units")
    ideal = sum(1/log2(i+2) for i in range(min(k, len(set(relevant)))))
    return sum(1/log2(i+2) for i, unit in enumerate(ranked[:k]) if unit in relevant) / ideal


def run(frozen, index, output):
    # The baseline verifies frozen dataset, index, evaluation-code hashes and human-review status.
    report = evaluate(frozen, index, output)
    data_bytes = (frozen.parent/"dataset.json").read_bytes()
    if hashlib.sha256(data_bytes).hexdigest() != report["dataset_sha256"]:
        raise ValueError("Frozen labels changed before nDCG scoring")
    data = json.loads(data_bytes)
    gold = {c["question_id"]: set(c["relevant_units"]) for c in data["cases"]}
    rows = []
    with (output/"predictions.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            p = json.loads(line)
            ids = [unit["unit_id"] for unit in p["ranked_units"]]
            relevant = gold[p["question_id"]]
            rows.append({"id":p["question_id"], "retrieval_ms":p["retrieval"]["latency_ms"],
                         "cuts":{str(k):{"ndcg": binary_ndcg(ids, relevant, k),
                         "missing_units":sorted(relevant-set(ids[:k]))} for k in report["policy"]["ks"]}})
    metrics = {k: dict(values, ndcg_at_k=mean(row["cuts"][k]["ndcg"] for row in rows))
               for k, values in report["metrics"].items()}
    result = {"dataset_sha256":report["dataset_sha256"], "metrics":metrics,
              "median_retrieval_ms":median(r["retrieval_ms"] for r in rows), "cases":rows}
    with (output/"quality.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for param in ("frozen", "index", "output"):
        p.add_argument("--"+param, type=Path, required=True)
    args = p.parse_args()
    run(args.frozen, args.index, args.output)
