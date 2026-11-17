import pytest

from scripts.evaluate_retrieval import evaluate, metrics


def test_hand_calculated_metrics():
    value = metrics(["b", "a"], {"a": 3, "b": 0, "c": 1}, 2)
    assert value["precision"] == value["recall"] == value["mrr"] == 0.5
    assert value["ndcg"] == pytest.approx((7 / __import__("math").log2(3)) / (7 + 1 / __import__("math").log2(3)))


def test_unjudged_not_negative_and_no_labels_not_evaluated():
    with pytest.raises(ValueError, match="Unjudged"):
        metrics(["x"], {"a": 1}, 1)
    result = evaluate(
        {"corpus_manifest": "demo", "queries": [{"id": "q", "qrels": None}]}, {"corpus_manifest": "demo"}, 5
    )
    assert result["status"] == "BLOCKED_NO_VALID_JUDGMENTS"


def test_zero_relevance_and_duplicate_ids():
    assert metrics(["a"], {"a": 0}, 5)["ndcg"] is None
    with pytest.raises(ValueError, match="Unique"):
        metrics(["a", "a"], {"a": 1}, 2)


def test_verified_synthetic_fixture_evaluates_four_configs_and_fixed_pool():
    query = {
        "id": "unit-only",
        "text": "synthetic",
        "as_of_date": "2026-11-16",
        "allowed_usage_policies": ["UNIT_ONLY"],
        "judgment_status": "VERIFIED",
        "annotator": "unit-fixture-not-human-experiment",
        "judgment_scope": "synthetic a/b",
        "qrels": {"a": 3, "b": 0},
    }
    run = {
        **query,
        "reranking_status": "APPLIED",
        "fixed_hybrid_pool": ["b", "a"],
        "rankings": {"bm25": ["b", "a"], "dense": ["a", "b"], "hybrid": ["b", "a"], "hybrid_reranked": ["a", "b"]},
    }
    dataset = {"corpus_manifest": "synthetic-unit-fixture", "queries": [query]}
    runs = {"corpus_manifest": "synthetic-unit-fixture", "queries": {"unit-only": run}}
    result = evaluate(dataset, runs, 1)
    assert result["status"] == "EVALUATED"
    assert result["queries"][0]["candidate_coverage"] == 1
    assert result["aggregate"]["hybrid_reranked"]["ndcg"]["mean"] == 1
    run["reranking_status"] = "FALLBACK"
    assert evaluate(dataset, runs, 1)["status"] == "BLOCKED_NO_VALID_JUDGMENTS"
