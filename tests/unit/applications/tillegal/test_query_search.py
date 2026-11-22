"""Offline orchestration with real RetrievalService and controlled read ports."""

import asyncio
from copy import deepcopy
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from src.applications.tillegal.agents.query.agent import QueryInputError, understand
from src.applications.tillegal.agents.search.agent import SearchOptions, search
from src.core.config import SupabaseSettings
from src.integrations.database.repositories.rpc import DatabaseRepositoryError
from src.query_search_bootstrap import QuerySearch, create_query_search
from tests.unit.applications.tillegal.retrieval.test_contracts import request
from tests.unit.applications.tillegal.retrieval.test_service import (
    FakeSparse,
    hydrated_service,
    service,
)


def options(**changes):
    return SearchOptions(
        mode="bm25", top_k=5, as_of_date=date(2026, 11, 10), allowed_usage_policies=("EXPERIMENTAL_ONLY",), **changes
    )


@pytest.mark.parametrize("question", ["Trích dẫn: đối thoại", "Người lao động nghỉ phép? Tiền lương năm 2024?"])
def test_real_service_fake_ports(question):
    svc, _, _ = hydrated_service()
    result = asyncio.run(QuerySearch(svc, options()).search(question))
    assert result["plan"] == understand(question)
    assert result["status"] == "COMPLETED"
    assert [r.query for r in result["requests"]] == [q["text"] for q in result["plan"]["subqueries"]]
    assert all(r.as_of_date == options().as_of_date for r in result["requests"])
    assert all(r.allowed_usage_policies == options().allowed_usage_policies for r in result["requests"])
    assert all(r.status == "OK" for r in result["responses"])
    row = result["responses"][0].evidence[0]
    assert row.retrieval_chunk_id.int == 2 and row.source_document_id.int == 30
    assert row.hash_check == "MATCHED_STORED" and row.source_url is None
    assert row.raw_score == 7.2 and row.content_representation == "retrieval_chunk_content"


@pytest.mark.parametrize("question", ["Có được không?", "31/02/2024"])
def test_clarification_no_reads(question):
    svc = AsyncMock()
    result = asyncio.run(QuerySearch(svc, options()).search(question))
    assert result["status"] == "CLARIFICATION_REQUIRED"
    assert result["requests"] == result["responses"] == ()
    svc.search.assert_not_called()


@pytest.mark.parametrize("question", [None, "", "a\0b"])
def test_invalid_input(question):
    svc = AsyncMock()
    with pytest.raises(QueryInputError):
        asyncio.run(QuerySearch(svc, options()).search(question))
    svc.search.assert_not_called()


def test_options_and_plan_fail_before_reads():
    svc = AsyncMock()
    data = options().model_dump()
    for changes in [
        {"top_k": 51},
        {"allowed_usage_policies": ()},
        {"allowed_usage_policies": (" ",)},
        {"as_of_date": None},
    ]:
        with pytest.raises(ValidationError):
            SearchOptions.model_validate({**data, **changes})
    with pytest.raises(ValidationError):
        asyncio.run(search({}, svc, options()))
    svc.search.assert_not_called()


def test_no_match_failure_and_no_fallback():
    assert asyncio.run(QuerySearch(service(), options()).search("Trích dẫn: thuế"))["responses"][0].status == "NO_MATCH"
    svc = service(sparse=FakeSparse(error=DatabaseRepositoryError("private")))
    state = asyncio.run(QuerySearch(svc, options()).search("thuế; nghỉ phép"))
    assert state["status"] == "FAILED" and len(state["responses"]) == 1
    assert state["responses"][0].error.category == "DATABASE_FAILURE"
    assert state["responses"][0].evidence == ()


def test_response_identity_and_plan_unchanged():
    response = asyncio.run(service().search(request()))
    svc = AsyncMock()
    svc.search.return_value = response
    plan = understand("Trích dẫn: thuế")
    before = deepcopy(plan)
    state = asyncio.run(search(plan, svc, options()))
    assert state["responses"][0] is response and plan == before


def test_bootstrap_delegates():
    svc = object()
    with patch("src.query_search_bootstrap.create_retrieval_service", return_value=svc) as factory:
        result = create_query_search(SupabaseSettings(), options())
    assert result.retrieval is svc
    assert factory.call_args.kwargs["dense_model_path"] is None


def test_no_legacy_imports():
    import inspect

    import src.applications.tillegal.agents.search.agent as agent
    import src.query_search_bootstrap as bootstrap

    assert "ai_core" not in inspect.getsource(agent)
    assert "ai_core" not in inspect.getsource(bootstrap)
