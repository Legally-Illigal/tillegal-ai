"""Offline semantics and evidence tests; no real LLM, database, or model inference."""

import asyncio
import json
from copy import deepcopy
from unittest.mock import AsyncMock

import pytest

from src.applications.tillegal.agents.query.agent import QueryPlan, understand
from src.applications.tillegal.agents.query.semantic import QueryAnalysisError, SemanticQueryAgent
from src.applications.tillegal.agents.search.agent import search
from src.applications.tillegal.retrieval.errors import RetrievalErrorDetail, RetrievalServiceError
from src.query_search_bootstrap import QuerySearch
from tests.unit.applications.tillegal.retrieval.test_service import hydrated_service
from tests.unit.applications.tillegal.test_query_search import options

QUESTION = (
    "Tôi ký hợp đồng lao động 2 năm, mới làm được 6 tháng nhưng muốn nghỉ việc. "
    "Tôi có phải báo trước không và có phải bồi thường không?"
)


def analysis(**changes):
    return {
        "intent": "legal_question",
        "domain": "labour",
        "facts": [{"text": "hợp đồng lao động 2 năm", "source_quote": "hợp đồng lao động 2 năm"}],
        "issues": [
            {"issue": "Nghĩa vụ báo trước", "search_query": "người lao động hợp đồng 2 năm nghỉ việc báo trước"},
            {"issue": "Bồi thường", "search_query": "người lao động hợp đồng 2 năm nghỉ việc bồi thường"},
        ],
        "missing_information": ["Lý do nghỉ việc là gì?"],
        "temporal_mentions": [],
        "clarification": None,
        **changes,
    }


def analyzer(data=None):
    complete = AsyncMock(return_value=json.dumps(analysis() if data is None else data, ensure_ascii=False))
    return SemanticQueryAgent(complete, model="fixture/structured-model"), complete


def test_offline_complex_and_implicit_issues_preserve_context():
    plan = understand(QUESTION)
    assert plan["analysis_method"] == "deterministic" and plan["analysis_model"] is None
    assert len(plan["subqueries"]) == len(plan["issues"]) == 2
    assert all("hợp đồng lao động 2 năm" in item["text"] for item in plan["subqueries"])
    assert "báo trước" in plan["subqueries"][0]["text"]
    assert "bồi thường" in plan["subqueries"][1]["text"]
    assert all(fact["text"] == fact["source_quote"] and fact["text"] in QUESTION for fact in plan["facts"])
    assert plan["missing_information"] and plan["clarification"] is None
    assert plan["original"] == QUESTION
    implicit = understand("Tôi muốn nghỉ việc theo hợp đồng lao động 2 năm")
    assert len(implicit["issues"]) == 2
    assert not understand("Thủ tục đăng ký đất đai?")["facts"]


def test_duplicate_objectives_collapsed_by_query():
    assert len(understand("tiền lương; tiền lương")["subqueries"]) == 1


@pytest.mark.parametrize("question", ["Tra cứu Điều 35 Bộ luật Lao động", "Tìm khoản 2 Điều 35 Bộ luật Lao động"])
def test_citation_lookup_preserves_user_reference_without_model(question):
    agent, complete = analyzer()
    plan = asyncio.run(agent.understand(question))
    assert plan["intent"] == "quote_lookup" and plan["subqueries"][0]["text"] == question
    complete.assert_not_awaited()


def test_contextual_citation_is_ordinary_question():
    assert understand("Tra cứu Điều 35 tôi có phải báo trước không?")["intent"] == "legal_question"


def test_semantic_json_contract_and_original():
    agent, complete = analyzer()
    plan = asyncio.run(agent.understand("  " + QUESTION + "  "))
    assert plan["original"] == "  " + QUESTION + "  "
    assert plan["analysis_method"] == "llm" and plan["analysis_model"] == "fixture/structured-model"
    assert len(plan["issues"]) == 2 and plan["facts"] == analysis()["facts"]
    assert plan["missing_information"][0] == analysis()["missing_information"][0]
    assert any("đào tạo" in item for item in plan["missing_information"])
    assert QueryPlan.model_validate_json(json.dumps(plan)).model_dump() == plan
    args = complete.call_args.kwargs
    assert args["schema"]["additionalProperties"] is False
    assert json.loads(args["user"])["question"] == QUESTION
    complete.assert_awaited_once()


@pytest.mark.parametrize("question", ["Có được không?", "Quy định ngày 31/02/2024", "Trích dẫn: nghỉ phép"])
def test_validation_and_exact_lookup_short_circuit_model(question):
    agent, complete = analyzer()
    assert asyncio.run(agent.understand(question)) == understand(question)
    complete.assert_not_awaited()


@pytest.mark.parametrize("raw", ["not json", "{}", "[]", "x" * 32001, None, 42])
def test_invalid_model_response_is_explicit_failure(raw):
    complete = AsyncMock(return_value=raw)
    with pytest.raises(QueryAnalysisError, match="^QUERY_ANALYSIS_INVALID_RESPONSE$"):
        asyncio.run(SemanticQueryAgent(complete, "fixture/model").understand(QUESTION))


@pytest.mark.parametrize(
    "change",
    [
        {"facts": [{"text": "bị ép nghỉ việc", "source_quote": "bị ép nghỉ việc"}]},
        {"facts": [{"text": "hợp đồng không xác định thời hạn", "source_quote": "hợp đồng lao động 2 năm"}]},
        {"temporal_mentions": ["2025"]},
        {"intent": "quote_lookup"},
        {"issues": [{"issue": "Điều 999", "search_query": "Điều 999 quy định gì"}]},
        {"issues": [{"issue": "Tra cứu", "search_query": "Luật 99/2025/QH15"}]},
        {"issues": [{"issue": "Tra cứu", "search_query": "   "}]},
        {"issues": []},
        {"missing_information": [" "]},
        {"extra": "ignored?"},
    ],
)
def test_reject_unsupported_or_invalid_semantics(change):
    agent, _ = analyzer(analysis(**change))
    with pytest.raises(QueryAnalysisError, match="^QUERY_ANALYSIS_INVALID_RESPONSE$"):
        asyncio.run(agent.understand(QUESTION))


def test_ordinary_legal_terminology_is_not_a_citation():
    data = analysis(issues=[{"issue": "Điều kiện nghỉ việc", "search_query": "điều kiện chấm dứt hợp đồng lao động"}])
    agent, _ = analyzer(data)
    assert asyncio.run(agent.understand(QUESTION))["analysis_method"] == "llm"


def test_user_citation_may_be_used_but_is_not_evidence():
    data = analysis(
        issues=[{"issue": "Tra cứu Điều 35", "search_query": "Điều 35 Bộ luật Lao động nghĩa vụ báo trước"}]
    )
    agent, _ = analyzer(data)
    plan = asyncio.run(agent.understand(QUESTION + " Theo Điều 35 thì sao?"))
    assert plan["analysis_method"] == "llm" and "evidence" not in plan


def test_model_time_is_extractive_and_not_execution_date():
    agent, _ = analyzer(analysis(temporal_mentions=["2024"]))
    plan = asyncio.run(agent.understand(QUESTION + " vào năm 2024"))
    assert plan["temporal_scope"] == ["2024"]
    assert "as_of_date" not in plan


def test_provider_failure_has_no_silent_fallback_or_secret():
    complete = AsyncMock(side_effect=RuntimeError("private provider diagnostic"))
    with pytest.raises(QueryAnalysisError, match="^QUERY_ANALYSIS_PROVIDER_ERROR$"):
        asyncio.run(SemanticQueryAgent(complete, "fixture/model").understand(QUESTION))
    complete.assert_awaited_once()


def test_semantic_timeout_and_cancellation():
    async def waiting(**kwargs):
        await asyncio.Event().wait()

    with pytest.raises(QueryAnalysisError, match="^QUERY_ANALYSIS_TIMEOUT$"):
        asyncio.run(SemanticQueryAgent(waiting, "fixture/model", timeout_seconds=0.01).understand(QUESTION))

    async def run():
        complete = AsyncMock(side_effect=asyncio.CancelledError)
        with pytest.raises(asyncio.CancelledError):
            await SemanticQueryAgent(complete, "fixture/model").understand(QUESTION)

    asyncio.run(run())


def native_response():
    service, *_ = hydrated_service()
    return asyncio.run(QuerySearch(service, options()).search("Trích dẫn: thuế"))["responses"][0]


def test_single_and_duplicate_requests_keep_associations_and_scores():
    response = native_response()
    retrieval = AsyncMock()
    retrieval.search.return_value = response
    plan = understand("Trích dẫn: thuế")
    plan["subqueries"] *= 2
    before = deepcopy(plan)
    result = asyncio.run(search(plan, retrieval, options()))
    assert result["status"] == "COMPLETED" and result["completeness"] == "COMPLETE"
    assert result["executed_searches"] == 1 and len(result["responses"]) == 2
    assert result["responses"][0] is result["responses"][1] is response
    assert len(result["evidence"]) == len(response.evidence)
    row = result["evidence"][0]
    assert [o.subquery_index for o in row.occurrences] == [0, 1]
    assert row.evidence is response.evidence[0]
    assert all(o.query == "thuế" and o.raw_score == row.evidence.raw_score for o in row.occurrences)
    assert plan == before


def test_multiple_queries_real_service_aggregate_metadata():
    service, *_ = hydrated_service()
    result = asyncio.run(QuerySearch(service, options()).search(QUESTION))
    assert result["executed_searches"] == 2 and len(result["evidence"]) == 2
    assert all(len(row.occurrences) == 2 for row in result["evidence"])
    assert result["evidence"][0].evidence.source_metadata == result["responses"][0].evidence[0].source_metadata
    assert result["evidence"][0].evidence.content_sha256 == result["responses"][0].evidence[0].content_sha256


@pytest.mark.parametrize(
    "change",
    [
        {"source_snapshot_id": "different-version"},
        {"source_metadata": {"amended": True}},
        {"content_sha256": "0" * 64, "content": "Different stored payload"},
        {"effective_to": options().as_of_date},
    ],
)
def test_conflicting_legal_versions_never_merge(change):
    response = native_response()
    changed = response.evidence[0].model_copy(update=change)
    second = response.model_copy(update={"evidence": (changed, *response.evidence[1:])})
    retrieval = AsyncMock()
    retrieval.search.side_effect = [response, second]
    plan = understand("thuế; nghỉ phép")
    result = asyncio.run(search(plan, retrieval, options()))
    assert len(result["evidence"]) == len(response.evidence) + 1
    assert "EVIDENCE_IDENTITY_CONFLICT" in result["warnings"]


def test_partial_failure_retains_evidence_and_explicit_skipped_queries():
    response = native_response()
    error = RetrievalErrorDetail(category="DATABASE_FAILURE", code="READ_FAILED", stage="search", message="Read failed")
    failure = response.model_copy(update={"status": "FAILED", "evidence": (), "error": error})
    retrieval = AsyncMock()
    retrieval.search.side_effect = [response, failure]
    result = asyncio.run(search(understand("thuế; nghỉ phép; đăng ký đất"), retrieval, options()))
    assert result["status"] == "FAILED" and result["completeness"] == "PARTIAL"
    assert result["skipped_subqueries"] == (2,) and result["executed_searches"] == 2
    assert result["evidence"] and result["errors"] == (error,)
    assert "SEARCH_INCOMPLETE" in result["warnings"]


def test_empty_search_is_complete_but_no_match_is_visible():
    from tests.unit.applications.tillegal.retrieval.test_service import service

    result = asyncio.run(QuerySearch(service(), options()).search("Trích dẫn: thuế"))
    assert result["completeness"] == "COMPLETE" and result["evidence"] == ()
    assert "NO_MATCH:0" in result["warnings"]


def test_search_deadline_and_classified_dependency_error():
    async def waiting(request):
        await asyncio.Event().wait()

    retrieval = AsyncMock()
    retrieval.search.side_effect = waiting
    result = asyncio.run(search(understand("thuế; nghỉ phép"), retrieval, options(), timeout_seconds=0.01))
    assert result["completeness"] == "FAILED" and result["skipped_subqueries"] == (1,)
    assert result["errors"][0].code == "SEARCH_QUERY_TIMEOUT"
    detail = RetrievalErrorDetail(category="DATABASE_FAILURE", code="PORT_FAILED", stage="search", message="Failure")
    retrieval.search.side_effect = RetrievalServiceError(detail)
    result = asyncio.run(search(understand("thuế; nghỉ phép"), retrieval, options()))
    assert result["errors"] == (detail,) and result["executed_searches"] == 1


def test_temporal_warning_and_caller_filter_preserved():
    service, *_ = hydrated_service()
    result = asyncio.run(QuerySearch(service, options()).search("nghỉ phép năm 2024"))
    assert "TEMPORAL_SCOPE_REQUIRES_CALLER_DATE_REVIEW" in result["warnings"]
    assert all(request.as_of_date == options().as_of_date for request in result["requests"])


def test_mocked_semantic_query_to_real_service_execution():
    service, *_ = hydrated_service()
    agent, complete = analyzer()
    result = asyncio.run(QuerySearch(service, options(), agent).search(QUESTION))
    assert result["plan"]["analysis_method"] == "llm" and result["status"] == "COMPLETED"
    assert result["executed_searches"] == 2 and len(result["responses"]) == 2
    assert all(response.status == "OK" for response in result["responses"])
    assert all(len(row.occurrences) == 2 for row in result["evidence"])
    complete.assert_awaited_once()


def test_citation_year_is_not_a_temporal_constraint():
    agent, _ = analyzer(analysis(temporal_mentions=["2019"]))
    plan = asyncio.run(agent.understand(QUESTION + " Theo Luật 45/2019/QH14 thì sao?"))
    assert "2019" not in plan["temporal_scope"]
    assert any(item["text"] == "45/2019/QH14" for item in plan["citations"])
    assert "MODEL_REFERENCE_RECLASSIFIED" in plan["planning_warnings"]


def test_new_numeric_user_facts_are_rejected():
    data = analysis(issues=[{"issue": "Báo trước", "search_query": "hợp đồng 3 năm báo trước 30 ngày"}])
    agent, _ = analyzer(data)
    with pytest.raises(QueryAnalysisError, match="^QUERY_ANALYSIS_INVALID_RESPONSE$"):
        asyncio.run(agent.understand(QUESTION))


def test_semantic_clarification_skips_retrieval():
    agent, _ = analyzer(analysis(clarification="Bạn đang hỏi về hợp đồng với bên nào?"))
    retrieval = AsyncMock()
    result = asyncio.run(QuerySearch(retrieval, options(), agent).search(QUESTION))
    assert result["completeness"] == "NOT_STARTED"
    assert result["status"] == "CLARIFICATION_REQUIRED" and not result["responses"]
    retrieval.search.assert_not_awaited()


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan")])
def test_invalid_deadline_rejected_before_model_or_retrieval(timeout):
    complete = AsyncMock()
    with pytest.raises(ValueError):
        SemanticQueryAgent(complete, "fixture/model", timeout_seconds=timeout)
    retrieval = AsyncMock()
    with pytest.raises(ValueError):
        asyncio.run(search(understand(QUESTION), retrieval, options(), timeout_seconds=timeout))
    complete.assert_not_awaited()
    retrieval.search.assert_not_awaited()


@pytest.mark.parametrize(
    "question",
    [
        "Công ty muốn chấm dứt hợp đồng lao động của tôi thì phải làm gì?",
        "Tôi không muốn nghỉ việc nhưng công ty chấm dứt hợp đồng lao động?",
        "Tôi bị sa thải khi làm việc theo hợp đồng lao động 2 năm?",
    ],
)
def test_offline_planner_does_not_invent_employee_exit_intent(question):
    plan = understand(question)
    assert plan["issues"] == [] and plan["facts"] == []
    assert not any("người lao động đơn phương" in item["text"] for item in plan["subqueries"])


def test_offline_exit_does_not_discard_other_question_parts():
    plan = understand("Tôi muốn nghỉ việc theo hợp đồng lao động 2 năm? Công ty nợ tiền lương thì sao?")
    assert any("Công ty nợ tiền lương" in item["text"] for item in plan["subqueries"])
