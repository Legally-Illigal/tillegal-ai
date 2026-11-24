"""Runtime Query grounding regressions; no evaluation datasets or live I/O."""

import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from src.applications.tillegal.agents.query.schemas import SemanticAnalysis
from src.applications.tillegal.agents.query.semantic import QueryAnalysisError, SemanticQueryAgent


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
