"""Relevance-label provenance must remain independent of retrieval/proxy scores."""

import pytest

from scripts.evaluate_query_relevance import label_status


def test_unlabeled_is_not_zero_and_never_becomes_expert_metric():
    result = label_status([{"review_id": "a"}, {"review_id": "b"}], [])
    assert result["counts"]["unlabeled"] == 2
    assert result["expert_precision_at_k"] is result["expert_recall_at_k"] is result["expert_ndcg"] is None


def test_provisional_and_human_labels_are_reported_separately():
    rows = [{"review_id": "a"}, {"review_id": "b"}]
    labels = [
        {
            "review_id": "a",
            "label": 1,
            "label_source": "model_assisted_provisional",
            "reviewer": "fixture-model",
            "reason": "fixture",
        },
        {
            "review_id": "b",
            "label": 3,
            "label_source": "human_reviewed",
            "reviewer": "fixture-reviewer",
            "reason": "fixture",
        },
    ]
    result = label_status(rows, labels)
    assert result["counts"] == {
        "human_reviewed": 1,
        "model_assisted_provisional": 1,
        "automatic_proxy": 0,
        "unlabeled": 0,
    }
    assert result["expert_ndcg"] is None


@pytest.mark.parametrize(
    "bad",
    [
        {"review_id": "unknown", "label": None},
        {"review_id": "a", "label": True, "label_source": "human_reviewed", "reviewer": "fixture", "reason": "fixture"},
        {"review_id": "a", "label": 4, "label_source": "human_reviewed", "reviewer": "fixture", "reason": "fixture"},
        {"review_id": "a", "label": 3, "label_source": "unlabeled", "reviewer": "fixture", "reason": "fixture"},
        {"review_id": "a", "label": 3, "label_source": "human_reviewed", "reviewer": None, "reason": None},
    ],
)
def test_unknown_score_or_missing_provenance_rejected(bad):
    with pytest.raises(ValueError):
        label_status([{"review_id": "a"}], [bad])


def test_task_budget_refuses_batch_before_any_model_call(tmp_path, monkeypatch):
    import argparse
    import asyncio
    import json
    from unittest.mock import AsyncMock

    import scripts.validate_query_semantics as evaluator

    monkeypatch.setattr(evaluator, "FOLDER", tmp_path)
    ledger = {"maximum": 25, "attempted": 24}
    (tmp_path / "api_budget.json").write_text(json.dumps(ledger), encoding="utf-8")
    execute = AsyncMock()
    monkeypatch.setattr(evaluator, "evaluate", execute)
    args = argparse.Namespace(mode="gemini", ids="Q004,Q025")
    with pytest.raises(ValueError, match="SEMANTIC_EVALUATION_BUDGET_INSUFFICIENT"):
        asyncio.run(evaluator.run(args))
    execute.assert_not_awaited()
    assert json.loads((tmp_path / "api_budget.json").read_text(encoding="utf-8")) == ledger
