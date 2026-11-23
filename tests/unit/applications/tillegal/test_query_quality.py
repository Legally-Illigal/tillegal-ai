"""Quality harness contracts and targeted Query regressions; no provider/database I/O."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from scripts.evaluate_query_search import aggregate, matches, objective_assignment
from scripts.evaluate_query_search_retrieval import sanitize
from src.applications.tillegal.agents.query.schemas import SemanticAnalysis
from src.applications.tillegal.agents.query.semantic import QueryAnalysisError, SemanticQueryAgent

ROOT = Path(__file__).resolve().parents[4]


def model_output(query="điều kiện có hiệu lực hợp đồng", **changes):
    return {
        "intent": "legal_question",
        "domain": "unknown",
        "facts": [],
        "issues": [{"issue": "Điều kiện có hiệu lực", "search_query": query}],
        "missing_information": [],
        "temporal_mentions": [],
        "clarification": None,
        **changes,
    }


def run(question, data):
    completion = AsyncMock(return_value=json.dumps(data, ensure_ascii=False))
    plan = asyncio.run(SemanticQueryAgent(completion, "fixture/model").understand(question))
    return plan, completion


def test_semantic_provider_schema_excludes_intent_that_runtime_already_rejects():
    plan, completion = run("Hợp đồng dân sự có hiệu lực khi nào?", model_output())
    assert completion.call_args.kwargs["schema"]["properties"]["intent"]["enum"] == ["legal_question"]
    # Public compatibility schema stays unchanged, including exact lookup.
    assert SemanticAnalysis.model_json_schema()["properties"]["intent"]["enum"] == ["quote_lookup", "legal_question"]
    assert plan["intent"] == "legal_question"


def test_single_objective_preserves_user_article_clause_and_document_identity():
    question = "Tôi muốn kiểm tra khoản 1 Điều 117 Bộ luật Dân sự 91/2015/QH13 có đúng như bài viết không?"
    plan, _ = run(question, model_output("điều kiện có hiệu lực Điều 117"))
    query = plan["subqueries"][0]["text"]
    assert all(reference in query for reference in ("khoản 1", "Điều 117", "91/2015/QH13"))
    assert query.count("Điều 117") == 1
    assert plan["original"] == question


def test_no_citation_invention_for_ordinary_question():
    plan, _ = run("Hợp đồng dân sự có hiệu lực khi nào?", model_output())
    assert plan["subqueries"][0]["text"] == "điều kiện có hiệu lực hợp đồng"


def test_multiple_objectives_do_not_receive_unrelated_citations():
    data = model_output(
        issues=[
            {"issue": "Hợp đồng", "search_query": "Điều 117 hợp đồng"},
            {"issue": "Lao động", "search_query": "Điều 35 nghỉ việc"},
        ]
    )
    plan, _ = run("Tôi hỏi Điều 117 Bộ luật Dân sự và Điều 35 Bộ luật Lao động thì sao?", data)
    assert "Điều 35" not in plan["subqueries"][0]["text"]
    assert "Điều 117" not in plan["subqueries"][1]["text"]


@pytest.mark.parametrize(
    "facts",
    [
        [{"text": "chuyển tiền", "source_quote": "chuyển tiền."}],
        [{"text": "đã chuyển khoản", "source_quote": "đã chuyển khoản"}],
    ],
)
def test_punctuation_or_paraphrased_facts_still_fail_strict_grounding(facts):
    completion = AsyncMock(return_value=json.dumps(model_output(facts=facts)))
    with pytest.raises(QueryAnalysisError, match="QUERY_ANALYSIS_INVALID_RESPONSE"):
        asyncio.run(
            SemanticQueryAgent(completion, "fixture/model").understand("Tôi đã chuyển tiền nhưng không nhận hàng.")
        )


def test_dataset_is_fixed_utf8_and_independently_grounded():
    cases = json.loads((ROOT / "evaluation/query_search/cases.json").read_text(encoding="utf-8"))["cases"]
    assert len(cases) == 45 and len({case["category"] for case in cases}) == 15
    assert len({case["id"] for case in cases}) == 45
    assert sum(case["live_sample"] for case in cases) == 15
    for case in cases:
        assert all(fact in case["question"] for fact in case["expected_preserved_facts"])
        assert all(citation in case["question"] for citation in case["citation_constraints"])


def test_objective_matching_does_not_reward_one_query_as_several_distinct_queries():
    assert objective_assignment(["báo trước", "bồi thường"], ["báo trước và bồi thường"]) == 1
    assert objective_assignment(["báo trước", "bồi thường"], ["báo trước", "bồi thường"]) == 2
    assert matches("A|bảo lãnh", "Trách nhiệm của B bảo lãnh")
    assert not matches("A", "trả")


def test_aggregation_retains_errors_in_denominator_and_labels_semantic_proxies():
    report = aggregate(
        [{"status": "ERROR", "latency_ms": 2, "api_calls": 1, "error": {"code": "QUERY_ANALYSIS_INVALID_RESPONSE"}}]
    )
    assert report["cases"] == report["failures"] == 1 and report["successes"] == 0
    assert report["issue_coverage_proxy"] is None
    assert report["semantic_grade"] == "HEURISTIC_REQUIRES_HUMAN_REVIEW"
    assert report["cost_usd"] is None


def test_nested_evidence_export_redacts_sensitive_metadata_keys():
    assert sanitize({"source": [{"authorization": "secret", "api_key": "secret", "title": "public"}]}) == {
        "source": [{"authorization": "[REDACTED]", "api_key": "[REDACTED]", "title": "public"}]
    }
