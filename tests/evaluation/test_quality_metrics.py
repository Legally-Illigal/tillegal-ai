"""Hand-calculated metrics and missing-ground-truth gates."""

import json
from math import log2

import pytest

from src.applications.tillegal.evaluation.annotations import Annotation, Prediction, Span
from src.applications.tillegal.evaluation.quality_metrics import (
    evaluate_case,
    percentile,
    retrieval,
    span_recall,
    summarize,
    wilson,
)


def annotation(kind="synthetic"):
    return Annotation(
        question_id="Q1",
        question="fixture",
        legal_domain="synthetic",
        query_intent="lookup",
        provenance=kind,
        temporal_applicability="UNKNOWN",
        relevant_units=["a", "b"],
        expected_abstention=True,
    )


def prediction():
    return Prediction(question_id="Q1", ranked_units=["x", "a", "b"], latency_ms=10, abstained=False)


def span(start=0, end=10, version="v1", role="evidence"):
    return Span(
        evidence_id="e",
        document_id="d",
        document_version_id=version,
        source_id="s",
        quote_sha256="a" * 64,
        article="1",
        clause=None,
        point=None,
        start=start,
        end=end,
        role=role,
    )


def test_retrieval_hand_calculated_and_empty_labels():
    metrics = retrieval(["x", "a", "b"], ["a", "b"], 2)
    assert metrics["recall"] == 0.5 and metrics["precision"] == 0.5 and metrics["mrr"] == 0.5
    assert metrics["ndcg"] == pytest.approx((1 / log2(3)) / (1 + 1 / log2(3)))
    assert retrieval([], None, 5) == dict(recall=None, precision=None, mrr=None, ndcg=None)
    assert retrieval([], [], 5)["recall"] is None
    assert retrieval(["a"], ["a"], 5)["precision"] == 0.2


def test_context_condition_exception_and_version():
    targets = [span(role="condition"), span(role="exception")]
    context = [span(0, 4), span(4, 10)]
    assert span_recall(targets, context) == 1
    assert span_recall(targets, context, "condition") == 1
    assert span_recall(targets, [span(0, 10, "v2")], "exception") == 0
    assert span_recall(targets, [span(0, 4), span(5, 10)]) == 0
    assert span_recall(None, context) is None


def test_review_gate_and_claim_counts():
    assert all(v is None for v in evaluate_case(annotation("draft"), prediction(), 2)["metrics"].values())
    assert evaluate_case(annotation(), prediction(), 2)["metrics"]["abstention_accuracy"] == 0
    with pytest.raises(ValueError):
        annotation("human_approved")
    a = annotation().model_copy(update={"claims": None})
    assert evaluate_case(a, prediction())["metrics"]["claim_support_accuracy"] is None
    a = Annotation.model_validate(
        dict(
            annotation().model_dump(),
            claims=[
                {"claim_id": "c", "verdict": "SUPPORTED", "evidence_ids": ["e"]},
                {"claim_id": "d", "verdict": "CONTRADICTED", "evidence_ids": ["e"]},
            ],
        )
    )
    p = Prediction.model_validate(
        dict(
            prediction().model_dump(),
            claims=[
                {"claim_id": "c", "verdict": "SUPPORTED", "evidence_ids": ["e"]},
                {"claim_id": "d", "verdict": "INSUFFICIENT_EVIDENCE", "evidence_ids": []},
            ],
        )
    )
    result = evaluate_case(a, p)
    assert result["metrics"]["claim_support_accuracy"] == 0.5
    assert result["metrics"]["citation_correctness"] == 1
    assert result["predicted_verdict_counts"]["CONTRADICTED"] == 0
    assert result["predicted_verdict_counts"]["INSUFFICIENT_EVIDENCE"] == 1


def test_latency_usage_cost_and_failure_coverage():
    assert percentile(list(range(1, 21)), 0.5) == 10 and percentile(list(range(1, 21)), 0.95) == 19
    p = prediction().model_copy(update={"prompt_tokens": 100, "completion_tokens": 20})
    failed = prediction().model_copy(update={"abstained": None, "failed": True})
    summary = summarize([p, failed])
    assert summary["abstention_coverage"] == 0.5 and summary["tokens"]["prompt_tokens"] is None
    assert summarize([p], {"prompt_tokens": 2, "completion_tokens": 5})["estimated_cost"] == pytest.approx(0.0003)
    assert wilson(10, 10, True) is None and wilson(50, 100, False) is None
    low, high = wilson(50, 100, True)
    assert low == pytest.approx(0.40383, abs=0.0001) and high == pytest.approx(0.59617, abs=0.0001)


def test_runner_classifies_synthetic_and_draft(tmp_path):
    from scripts.evaluate_quality import run

    labels = tmp_path / "labels.json"
    preds = tmp_path / "preds.json"
    config = tmp_path / "config.json"
    labels.write_text(json.dumps([annotation("draft").model_dump()]))
    preds.write_text(json.dumps([prediction().model_dump()]))
    config.write_text(
        json.dumps(
            {
                "dataset_version": "fixture-v1",
                "index_version": "v1",
                "index_sha256": "a" * 64,
                "model": "mock",
                "model_revision": None,
                "retrieval_config": {"mode": "bm25"},
                "prompt_version": "v1",
                "configuration_version": "v1",
                "workflow": "draft",
            }
        )
    )
    report = run(labels, preds, config, tmp_path / "out.json")
    assert report["classifications"]["draft"]["macro_metrics"]["recall"]["value"] is None
    assert report["operational"]["latency_p95_ms"] == 10
    with pytest.raises(ValueError):
        run(labels, preds, config, tmp_path / "out.json")
    settings = json.loads(config.read_text())
    settings["price_per_million"] = {"prompt_tokens": 2, "completion_tokens": 5}
    config.write_text(json.dumps(settings))
    preds.write_text(json.dumps([dict(prediction().model_dump(), prompt_tokens=100, completion_tokens=20)]))
    report = run(labels, preds, config, tmp_path / "priced.json")
    assert report["operational"]["estimated_cost"] == pytest.approx(0.0003)
