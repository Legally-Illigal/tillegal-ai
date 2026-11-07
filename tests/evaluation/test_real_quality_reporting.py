"""Technical reporting must separate abstention, provider failure and legal quality."""

import json

import pytest

from scripts.summarize_real_quality import category, summarize


def test_failure_is_not_abstention_or_claim_accuracy():
    assert (
        category({"result": {"status": "FAILED", "error": "PROVIDER_TIMEOUT"}})
        == "generation_or_runtime:PROVIDER_TIMEOUT"
    )
    row = {"result": {"status": "ABSTAINED", "judgments": [{"selected": ["e"]}], "citation_checks": []}}
    assert category(row) == "model_abstention"
    row["result"]["citation_checks"] = [{"claim_support": "NOT_EVALUATED"}]
    assert category(row) == "verification_or_publication_rejection"


def test_incomplete_experiment_cannot_be_summarized(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"cases": [{"id": "q"}], "policies": ["context"]}))
    with pytest.raises(ValueError, match="incomplete"):
        summarize(tmp_path)
