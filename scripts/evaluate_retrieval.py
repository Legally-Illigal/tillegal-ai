"""Offline evaluation of saved rankings with human qrels; never invent missing judgments."""

import argparse
import json
import math
from pathlib import Path


def metrics(ranking: list[str], qrels: dict[str, int], k: int) -> dict[str, float | None]:
    if len(set(ranking)) != len(ranking) or k < 1:
        raise ValueError("Unique ranked IDs and positive K required")
    if any(type(g) is not int or not 0 <= g <= 3 for g in qrels.values()):
        raise ValueError("Human grades must be integers 0-3")
    top = ranking[:k]
    if any(cid not in qrels for cid in top):
        raise ValueError("Unjudged candidates cannot silently become negatives")
    relevant = {cid for cid, grade in qrels.items() if grade > 0}
    hits = sum(cid in relevant for cid in top)
    dcg = sum((2 ** qrels[cid] - 1) / math.log2(i + 2) for i, cid in enumerate(top))
    ideal = sum((2**grade - 1) / math.log2(i + 2) for i, grade in enumerate(sorted(qrels.values(), reverse=True)[:k]))
    return {
        "precision": hits / k,
        "recall": hits / len(relevant) if relevant else None,
        "mrr": next((1 / i for i, cid in enumerate(top, 1) if cid in relevant), 0.0),
        "ndcg": dcg / ideal if ideal else None,
    }


def evaluate(dataset: dict, runs: dict, k: int) -> dict:
    if dataset["corpus_manifest"] != runs["corpus_manifest"]:
        raise ValueError("Corpus manifest mismatch")
    rows, excluded = [], []
    modes = ("bm25", "dense", "hybrid", "hybrid_reranked")
    for query in dataset["queries"]:
        qid = query["id"]
        if query.get("judgment_status") != "VERIFIED" or not query.get("qrels"):
            excluded.append({"id": qid, "reason": "UNVERIFIED_JUDGMENTS"})
            continue
        if not dataset["corpus_manifest"] or str(dataset["corpus_manifest"]).startswith("UNPINNED"):
            raise ValueError("Verified judgments require a pinned corpus manifest")
        run = runs["queries"][qid]
        for field in ("text", "as_of_date", "allowed_usage_policies"):
            if query[field] != run[field]:
                raise ValueError("Query/filter context mismatch")
        if not query.get("annotator") or not query.get("judgment_scope"):
            raise ValueError("Human annotation provenance/scope required")
        if run.get("reranking_status") != "APPLIED":
            excluded.append({"id": qid, "reason": "NO_APPLIED_CROSS_ENCODER_RUN"})
            continue
        qrels = query["qrels"]
        pool = run["fixed_hybrid_pool"]
        if len(set(pool)) != len(pool) or not set(run["rankings"]["hybrid_reranked"]).issubset(pool):
            raise ValueError("Reranked output must be a subset of the fixed pool")
        try:
            per_mode = {mode: metrics(run["rankings"][mode], qrels, k) for mode in modes}
            # Fixed-pool comparison uses saved order, not an independently re-retrieved list.
            rrf_fixed = metrics(pool, qrels, k)
        except ValueError as error:
            if "Unjudged" not in str(error):
                raise
            excluded.append({"id": qid, "reason": "INCOMPLETE_JUDGMENTS"})
            continue
        relevant = {cid for cid, g in qrels.items() if g > 0}
        rows.append(
            {
                "id": qid,
                "metrics": per_mode,
                "fixed_pool_rrf": rrf_fixed,
                "candidate_coverage": len(set(pool) & relevant) / len(relevant) if relevant else None,
            }
        )
    aggregate = {}
    for mode in modes:
        aggregate[mode] = {}
        for metric in ("precision", "recall", "mrr", "ndcg"):
            values = [row["metrics"][mode][metric] for row in rows if row["metrics"][mode][metric] is not None]
            aggregate[mode][metric] = {"mean": sum(values) / len(values) if values else None, "count": len(values)}
    return {
        "status": "EVALUATED" if rows else "BLOCKED_NO_VALID_JUDGMENTS",
        "k": k,
        "queries": rows,
        "excluded": excluded,
        "aggregate": aggregate,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(
        json.loads(args.dataset.read_text(encoding="utf-8")), json.loads(args.runs.read_text(encoding="utf-8")), args.k
    )
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
