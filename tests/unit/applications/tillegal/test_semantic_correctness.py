"""Grounded citation/time semantics and issue provenance. No model or DB I/O."""

import asyncio
import json
import unicodedata
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from src.applications.tillegal.agents.query.agent import QueryPlan, understand
from src.applications.tillegal.agents.query.context import parse_context, reconcile_missing
from src.applications.tillegal.agents.query.semantic import QueryAnalysisError, SemanticQueryAgent
from src.applications.tillegal.agents.search.agent import search
from tests.unit.applications.tillegal.retrieval.test_service import hydrated_service
from tests.unit.applications.tillegal.test_query_search import options


def response(**changes):
    return {
        "intent": "legal_question",
        "domain": "unknown",
        "facts": [],
        "issues": [{"issue": "Mục tiêu tìm kiếm", "search_query": "quy định liên quan"}],
        "missing_information": [],
        "temporal_mentions": [],
        "clarification": None,
        **changes,
    }


def analyze(question, data):
    complete = AsyncMock(return_value=json.dumps(data, ensure_ascii=False))
    return asyncio.run(SemanticQueryAgent(complete, "fixture/model").understand(question))


@pytest.mark.parametrize(
    "question,reference,time",
    [
        ("Tôi hỏi Luật 45/2019/QH14 có nội dung nào?", "45/2019/QH14", None),
        ("Tôi hỏi Điều 35 Bộ luật Lao động 2019 áp dụng ra sao?", "Bộ luật Lao động 2019", None),
        ("Tôi muốn kiểm tra Khoản 2 Điều 10 có đúng không?", "Khoản 2", None),
        ("Tôi ký ngày 15/03/2024 và muốn kiểm tra Điều 35 Luật 45/2019/QH14.", "45/2019/QH14", "15/03/2024"),
        ("Giao dịch diễn ra năm 2010 và tôi cần tìm quy định khi đó.", None, "2010"),
        ("Tôi kiểm tra Điều 35 Luật 45/2019/QH14 và Điều 117 Luật 91/2015/QH13.", "91/2015/QH13", None),
        ("Một bài viết dẫn Điều 35 Luật 45/2019/QH14, tôi muốn kiểm tra nhận định đó.", "45/2019/QH14", None),
        ("Tôi muốn tìm hiểu Bộ luật Dân sự 2015.", "Bộ luật Dân sự 2015", None),
    ],
)
def test_reference_identity_never_becomes_applicability_date(question, reference, time):
    plan = analyze(question, response())
    assert plan["original"] == question and plan["analysis_method"] == "llm"
    if reference:
        assert any(item["text"] == reference for item in plan["citations"])
    if time:
        assert any(item["text"] == time for item in plan["temporal_context"])
    assert all("/QH" not in item["text"] for item in plan["temporal_context"])
    assert not any(item["role"] == "applicability_date" for item in plan["temporal_context"])


def test_grounded_reference_in_model_time_is_reclassified_with_warning():
    question = "Tôi muốn kiểm tra Điều 35 Luật 45/2019/QH14, hợp đồng ký ngày 15/03/2024."
    plan = analyze(question, response(temporal_mentions=["45/2019/QH14", "2019", "15/03/2024"]))
    assert plan["temporal_scope"] == ["15/03/2024"]
    assert "MODEL_REFERENCE_RECLASSIFIED" in plan["planning_warnings"]
    assert "45/2019/QH14" in plan["subqueries"][0]["text"]
    assert all(item["source"] == "user_supplied_unverified" for item in plan["citations"])


def test_same_year_in_statute_and_event_is_not_removed():
    plan = analyze("Tôi theo Bộ luật Lao động 2019, hợp đồng ký năm 2019.", response(temporal_mentions=["2019"]))
    assert "2019" in plan["temporal_scope"]
    assert any(item["text"] == "2019" and item["role"] == "event_date" for item in plan["temporal_context"])
    assert any(item["kind"] == "statute_reference" for item in plan["citations"])


@pytest.mark.parametrize(
    "prefix,role",
    [
        ("ký ngày", "event_date"),
        ("áp dụng tại ngày", "applicability_date"),
        ("ban hành ngày", "publication_date"),
        ("có hiệu lực từ", "effective_date"),
    ],
)
def test_explicit_temporal_roles_do_not_infer_dates(prefix, role):
    question = f"Tôi hỏi văn bản {prefix} 01/02/2024 thì sao?"
    plan = analyze(question, response())
    mention = next(item for item in plan["temporal_context"] if item["text"] == "01/02/2024")
    assert mention["role"] == role and mention["iso_date"] == "2024-02-01"
    assert "as_of_date" not in plan


@pytest.mark.parametrize("mention", ["2027", "01/01/2000", "99/2026/QH15"])
def test_unsupported_time_or_source_still_rejected(mention):
    with pytest.raises(QueryAnalysisError, match="QUERY_ANALYSIS_INVALID_RESPONSE"):
        analyze("Tôi muốn kiểm tra Luật 45/2019/QH14.", response(temporal_mentions=[mention]))


def test_calendar_date_must_not_be_parsed_as_document_number():
    refs, times = parse_context("Tôi ký ngày 15/03/2024 theo Luật 45/2019/QH14.")
    assert all(item.text != "15/03/2024" for item in refs)
    assert any(item.text == "15/03/2024" for item in times)


def test_original_unicode_offsets_are_documented_analysis_offsets():
    question = unicodedata.normalize("NFD", "  Tôi hỏi Điều 35 Bộ luật Lao động 2019.  ")
    plan = understand(question)
    assert plan["original"] == question
    normalized = unicodedata.normalize("NFC", question).strip()
    assert all(normalized[item["start"] : item["end"]] == item["text"] for item in plan["citations"])


def test_known_contract_duration_does_not_remove_other_missing_context():
    text = "Tôi ký hợp đồng lao động 2 năm và muốn nghỉ việc."
    missing, warnings = reconcile_missing(
        text, ["Thời hạn hợp đồng là bao lâu?", "Loại hợp đồng có thỏa thuận đặc biệt không?"]
    )
    assert "Thời hạn hợp đồng là bao lâu?" not in missing
    assert "Loại hợp đồng có thỏa thuận đặc biệt không?" in missing
    assert any("lý do" in item for item in missing) and any("đào tạo" in item for item in missing)
    assert "REDUNDANT_CONTRACT_DURATION_REMOVED" in warnings


def test_provided_reason_training_and_duration_are_not_requested_again():
    question = (
        "Tôi ký hợp đồng lao động xác định thời hạn 24 tháng, muốn nghỉ vì chuyển nhà và không có thỏa thuận đào tạo."
    )
    missing, _ = reconcile_missing(
        question, ["Loại hợp đồng là gì?", "Lý do nghỉ là gì?", "Có thỏa thuận đào tạo không?"]
    )
    assert missing == []


def test_each_objective_gets_grounded_shared_facts_and_evidence_links():
    question = "Tôi ký hợp đồng lao động 2 năm, mới làm được 6 tháng và muốn nghỉ việc."
    data = response(
        domain="labour",
        facts=[
            {"text": "hợp đồng lao động 2 năm", "source_quote": "hợp đồng lao động 2 năm"},
            {"text": "6 tháng", "source_quote": "6 tháng"},
        ],
        issues=[
            {"issue": "Báo trước", "search_query": "nghĩa vụ báo trước"},
            {"issue": "Bồi thường", "search_query": "nghĩa vụ bồi thường"},
        ],
    )
    plan = analyze(question, data)
    assert all("2 năm" in item["text"] and "6 tháng" in item["text"] for item in plan["subqueries"])
    assert plan["search_objectives"] == [
        {"query_index": 0, "issue_indices": [0]},
        {"query_index": 1, "issue_indices": [1]},
    ]
    service, *_ = hydrated_service()
    result = asyncio.run(search(plan, service, options()))
    assert result["status"] == "COMPLETED"
    assert all([item.issue_indices for item in group.occurrences] == [(0,), (1,)] for group in result["evidence"])


def test_related_issues_can_share_a_query_without_extra_calls():
    plan = analyze(
        "Tôi hỏi về trách nhiệm vay tiền và bảo lãnh.",
        response(
            issues=[
                {"issue": "Nợ vay", "search_query": "vay tiền bảo lãnh"},
                {"issue": "Bảo lãnh", "search_query": "vay tiền bảo lãnh"},
            ]
        ),
    )
    assert len(plan["subqueries"]) == 1 and plan["search_objectives"][0]["issue_indices"] == [0, 1]


def test_invalid_issue_link_rejected_and_old_plans_remain_loadable():
    plan = understand("Tra cứu Điều 35 Bộ luật Lao động")
    old = {
        key: value
        for key, value in plan.items()
        if key not in {"citations", "temporal_context", "search_objectives", "planning_warnings"}
    }
    assert QueryPlan.model_validate(old).search_objectives == []
    with pytest.raises(ValidationError):
        QueryPlan.model_validate({**plan, "search_objectives": [{"query_index": 0, "issue_indices": [2]}]})


def test_negated_current_reference_does_not_override_historical_need():
    plan = analyze(
        "Giao dịch năm 2010, tôi hỏi quy định khi đó, không phải hiện nay.",
        response(temporal_mentions=["2010", "hiện nay"]),
    )
    assert "2010" in plan["temporal_scope"] and "hiện nay" not in plan["temporal_scope"]
    assert any(item["text"] == "hiện nay" and item["negated"] for item in plan["temporal_context"])
    assert "NEGATED_TEMPORAL_REFERENCE_IGNORED" in plan["planning_warnings"]


def test_cross_reference_does_not_confirm_exact_lookup_source_identity():
    service, *_ = hydrated_service()
    plan = understand("Tra cứu Điều 35 Bộ luật Lao động 45/2019/QH14.")
    result = asyncio.run(search(plan, service, options()))
    assert result["status"] == "COMPLETED" and result["evidence"]
    assert "EXACT_LOOKUP_SOURCE_IDENTITY_UNCONFIRMED" in result["warnings"]


def test_literal_source_title_confirms_only_identity_not_legal_correctness():
    from tests.unit.applications.tillegal.retrieval.test_service import source_row

    service, *_ = hydrated_service(source=source_row(title="Bộ luật Lao động 45/2019/QH14"))
    result = asyncio.run(search(understand("Tra cứu Điều 35 Bộ luật Lao động 45/2019/QH14."), service, options()))
    assert "EXACT_LOOKUP_SOURCE_IDENTITY_UNCONFIRMED" not in result["warnings"]
    assert all(item.evidence.hash_check == "MATCHED_STORED" for item in result["evidence"])
